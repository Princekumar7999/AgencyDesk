from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas, auth

router = APIRouter(prefix="/agencies", tags=["Agencies"])

@router.post("", response_model=schemas.AgencyOut, status_code=status.HTTP_201_CREATED)
def create_agency(
    payload: schemas.AgencyCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Create the agency
    agency = models.Agency(name=payload.name)
    db.add(agency)
    db.flush()
    
    # Establish the user as agency_admin
    membership = models.AgencyMembership(
        user_id=current_user.id,
        agency_id=agency.id,
        role="agency_admin"
    )
    db.add(membership)
    db.commit()
    db.refresh(agency)
    return agency

# ----------------------------------------------------
# CLIENT MANAGEMENT
# ----------------------------------------------------
@router.post("/clients", response_model=schemas.ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: schemas.ClientCreate,
    membership: models.AgencyMembership = Depends(auth.require_roles(["agency_admin"])),
    db: Session = Depends(get_db)
):
    client = models.Client(
        agency_id=membership.agency_id,
        name=payload.name
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client

@router.get("/clients", response_model=List[schemas.ClientOut])
def list_clients(
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
    db: Session = Depends(get_db)
):
    if membership.role == "client_user":
        # Client user can only see their own client record
        clients = db.query(models.Client).filter(
            models.Client.id == membership.client_id,
            models.Client.agency_id == membership.agency_id
        ).all()
    else:
        # Agency admin/member can see all clients in the agency
        clients = db.query(models.Client).filter(
            models.Client.agency_id == membership.agency_id
        ).all()
    return clients

# ----------------------------------------------------
# MEMBER MANAGEMENT
# ----------------------------------------------------
@router.get("/members", response_model=List[schemas.MembershipOut])
def list_agency_members(
    membership: models.AgencyMembership = Depends(auth.require_roles(["agency_admin", "agency_member"])),
    db: Session = Depends(get_db)
):
    # Returns memberships and user details in this agency
    members = db.query(models.AgencyMembership).filter(
        models.AgencyMembership.agency_id == membership.agency_id
    ).all()
    return members

@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_agency_member(
    user_id: str,
    membership: models.AgencyMembership = Depends(auth.require_roles(["agency_admin"])),
    db: Session = Depends(get_db)
):
    # Prevent self-removal
    if user_id == membership.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself from the agency."
        )
        
    # Find the membership to remove
    target_membership = db.query(models.AgencyMembership).filter(
        models.AgencyMembership.user_id == user_id,
        models.AgencyMembership.agency_id == membership.agency_id
    ).first()
    
    if not target_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this agency."
        )
        
    # Transactional execution of removing a team member:
    # 1. Unassign all their tasks within this agency (assignee_id = NULL)
    db.query(models.Task).filter(
        models.Task.assignee_id == user_id,
        models.Task.agency_id == membership.agency_id
    ).update({models.Task.assignee_id: None}, synchronize_session=False)
    
    # 2. Remove them from all project memberships in this agency
    projects_in_agency = db.query(models.Project.id).filter(
        models.Project.agency_id == membership.agency_id
    ).subquery()
    
    db.query(models.ProjectMember).filter(
        models.ProjectMember.user_id == user_id,
        models.ProjectMember.project_id.in_(projects_in_agency)
    ).delete(synchronize_session=False)
    
    # 3. Delete their agency membership
    db.delete(target_membership)
    db.commit()
    return
