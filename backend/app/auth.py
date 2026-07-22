import os
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import OAuth2PasswordBearer
import jwt
import bcrypt
from sqlalchemy.orm import Session

from .database import get_db, current_user_id
from . import models

# Security Configurations
SECRET_KEY = os.getenv("JWT_SECRET", "agencydesk_secret_key_for_interview_prod_ready_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 Hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
        
    # Seed current_user_id context var and Session.info for audit logging
    db.info["current_user_id"] = user.id
    current_user_id.set(user.id)
    return user

def get_current_membership(
    x_agency_id: str = Header(..., description="Active Agency Tenant ID"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> models.AgencyMembership:
    membership = db.query(models.AgencyMembership).filter(
        models.AgencyMembership.user_id == current_user.id,
        models.AgencyMembership.agency_id == x_agency_id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You are not a member of this agency."
        )
        
    # Re-verify and lock the ContextVar and Session.info for any audit columns triggered in this request
    db.info["current_user_id"] = current_user.id
    current_user_id.set(current_user.id)
    return membership

def require_roles(allowed_roles: List[str]):
    def dependency(
        membership: models.AgencyMembership = Depends(get_current_membership)
    ) -> models.AgencyMembership:
        if membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied: Required roles: {', '.join(allowed_roles)}. Your role: {membership.role}"
            )
        return membership
    return dependency
