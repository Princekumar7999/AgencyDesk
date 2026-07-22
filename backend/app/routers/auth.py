from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db, current_user_id
from .. import models, schemas, auth

router = APIRouter(prefix="/auth", tags=["Authentication"])

class RegisterPayload(schemas.UserCreate):
    agency_name: Optional[str] = None

@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterPayload, db: Session = Depends(get_db)):
    # Check if email is already taken
    existing_user = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )
        
    # Create the user
    hashed_password = auth.get_password_hash(payload.password)
    user = models.User(
        email=payload.email,
        password_hash=hashed_password,
        full_name=payload.full_name
    )
    db.add(user)
    db.flush()  # flush to generate user.id
    
    current_user_id.set(user.id)
    
    # If agency_name is provided, automatically bootstrap a new agency and membership
    if payload.agency_name:
        agency = models.Agency(name=payload.agency_name)
        db.add(agency)
        db.flush() # flush to get agency.id
        
        # Admin membership
        membership = models.AgencyMembership(
            user_id=user.id,
            agency_id=agency.id,
            role="agency_admin"
        )
        db.add(membership)
        
    db.commit()
    db.refresh(user)
    return user

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = auth.create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
def get_me(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    # Load all memberships and associated agency details
    memberships = db.query(models.AgencyMembership).filter(
        models.AgencyMembership.user_id == current_user.id
    ).all()
    
    membership_details = []
    for m in memberships:
        agency = db.query(models.Agency).filter(models.Agency.id == m.agency_id).first()
        client_name = None
        if m.client_id:
            client = db.query(models.Client).filter(models.Client.id == m.client_id).first()
            if client:
                client_name = client.name
                
        membership_details.append({
            "agency_id": m.agency_id,
            "agency_name": agency.name if agency else "Unknown",
            "role": m.role,
            "client_id": m.client_id,
            "client_name": client_name
        })
        
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "memberships": membership_details
    }
