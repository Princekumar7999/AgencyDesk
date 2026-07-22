import uuid
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db, current_user_id
from .. import models, schemas, auth

router = APIRouter(prefix="/invites", tags=["Invitations"])

def generate_invite_token() -> str:
    return str(uuid.uuid4())

@router.post("", response_model=schemas.InvitationOut, status_code=status.HTTP_201_CREATED)
def invite_user(
    payload: schemas.InvitationCreate,
    membership: models.AgencyMembership = Depends(auth.require_roles(["agency_admin"])),
    db: Session = Depends(get_db)
):
    # If role is client_user, client_id must be provided
    if payload.role == "client_user" and not payload.client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_id is required when role is client_user."
        )
        
    # Verify client belongs to active agency
    if payload.client_id:
        client = db.query(models.Client).filter(
            models.Client.id == payload.client_id,
            models.Client.agency_id == membership.agency_id
        ).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid client_id: Client does not belong to this agency."
            )
            
    # Check if user already has a membership in this agency
    existing_member_user = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing_member_user:
        existing_membership = db.query(models.AgencyMembership).filter(
            models.AgencyMembership.user_id == existing_member_user.id,
            models.AgencyMembership.agency_id == membership.agency_id
        ).first()
        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this agency."
            )
            
    # Solve Invite Race: Look for active pending invite for (agency_id, email)
    # If found, upsert: update token, expiration, and role details.
    pending_invite = db.query(models.Invitation).filter(
        models.Invitation.agency_id == membership.agency_id,
        models.Invitation.email == payload.email,
        models.Invitation.accepted_at == None
    ).first()
    
    expires_at_time = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    
    if pending_invite:
        pending_invite.token = generate_invite_token()
        pending_invite.expires_at = expires_at_time
        pending_invite.role = payload.role
        pending_invite.client_id = payload.client_id
        db.commit()
        db.refresh(pending_invite)
        return pending_invite
        
    # Create new invitation
    invitation = models.Invitation(
        agency_id=membership.agency_id,
        client_id=payload.client_id,
        email=payload.email,
        role=payload.role,
        token=generate_invite_token(),
        expires_at=expires_at_time
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation

@router.get("/{token}", response_model=schemas.InviteDetailsOut)
def get_invite_details(token: str, db: Session = Depends(get_db)):
    invitation = db.query(models.Invitation).filter(
        models.Invitation.token == token
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation token not found."
        )
        
    if invitation.accepted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has already been accepted."
        )
        
    if invitation.expires_at < datetime.datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation token has expired."
        )
        
    agency = db.query(models.Agency).filter(models.Agency.id == invitation.agency_id).first()
    client_name = None
    if invitation.client_id:
        client = db.query(models.Client).filter(models.Client.id == invitation.client_id).first()
        if client:
            client_name = client.name
            
    return {
        "agency_name": agency.name if agency else "Unknown Agency",
        "email": invitation.email,
        "role": invitation.role,
        "client_name": client_name
    }

@router.post("/{token}/accept")
def accept_invitation(token: str, payload: schemas.InviteAccept, db: Session = Depends(get_db)):
    # To handle races, accept logic is wrapped in a transaction block
    # Query the invitation using FOR UPDATE to prevent double-accept races.
    # Note: SQLite does not support standard SELECT FOR UPDATE, but defaults to table locks on write.
    # We will do standard querying and verification, followed by atomic updates.
    
    invitation = db.query(models.Invitation).filter(
        models.Invitation.token == token
    ).with_for_update().first() if db.bind.name != "sqlite" else db.query(models.Invitation).filter(
        models.Invitation.token == token
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation token not found."
        )
        
    if invitation.accepted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has already been accepted."
        )
        
    if invitation.expires_at < datetime.datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired."
        )
        
    # Mark as accepted
    invitation.accepted_at = datetime.datetime.utcnow()
    
    # Check if user already exists
    user = db.query(models.User).filter(models.User.email == invitation.email).first()
    
    if not user:
        # Create new user
        hashed_password = auth.get_password_hash(payload.password)
        user = models.User(
            email=invitation.email,
            password_hash=hashed_password,
            full_name=payload.full_name
        )
        db.add(user)
        db.flush() # generate user.id
    else:
        # User exists: verify credentials to check they are the correct user
        if not auth.verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password for the existing account associated with this email."
            )
            
    # Set context user ID for audit columns (the invitee themselves is updating/creating)
    current_user_id.set(user.id)
    
    # Double check membership to prevent unique constraint failures
    existing_membership = db.query(models.AgencyMembership).filter(
        models.AgencyMembership.user_id == user.id,
        models.AgencyMembership.agency_id == invitation.agency_id
    ).first()
    
    if existing_membership:
        db.commit() # commit invitation accepted_at
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of this agency."
        )
        
    # Create Membership
    membership = models.AgencyMembership(
        user_id=user.id,
        agency_id=invitation.agency_id,
        role=invitation.role,
        client_id=invitation.client_id
    )
    db.add(membership)
    db.commit()
    
    # Generate immediate session token
    access_token = auth.create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}
