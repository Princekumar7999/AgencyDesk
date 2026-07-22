from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas, auth

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("", response_model=schemas.ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: schemas.ProjectCreate,
    membership: models.AgencyMembership = Depends(auth.require_roles(["agency_admin"])),
    db: Session = Depends(get_db)
):
    # Verify that the client belongs to the active agency
    client = db.query(models.Client).filter(
        models.Client.id == payload.client_id,
        models.Client.agency_id == membership.agency_id
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Client: Client does not exist or does not belong to this agency."
        )
        
    project = models.Project(
        agency_id=membership.agency_id,
        client_id=payload.client_id,
        name=payload.name,
        description=payload.description
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Reload with client relation
    project_out = db.query(models.Project).filter(models.Project.id == project.id).first()
    return project_out

@router.get("", response_model=List[schemas.ProjectOut])
def list_projects(
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
    db: Session = Depends(get_db)
):
    if membership.role == "agency_admin":
        # Full access
        projects = db.query(models.Project).filter(
            models.Project.agency_id == membership.agency_id
        ).all()
    elif membership.role == "agency_member":
        # Only projects they are assigned to
        projects = db.query(models.Project).join(
            models.ProjectMember, models.ProjectMember.project_id == models.Project.id
        ).filter(
            models.Project.agency_id == membership.agency_id,
            models.ProjectMember.user_id == membership.user_id
        ).all()
    elif membership.role == "client_user":
        # Only projects belonging to their client
        projects = db.query(models.Project).filter(
            models.Project.agency_id == membership.agency_id,
            models.Project.client_id == membership.client_id
        ).all()
    else:
        projects = []
        
    return projects

@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(
    project_id: str,
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
    db: Session = Depends(get_db)
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.agency_id == membership.agency_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found."
        )
        
    # Role-based access validation
    if membership.role == "agency_member":
        # Check if project member
        is_member = db.query(models.ProjectMember).filter(
            models.ProjectMember.project_id == project_id,
            models.ProjectMember.user_id == membership.user_id
        ).first()
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this project."
            )
    elif membership.role == "client_user":
        # Check client alignment
        if project.client_id != membership.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: This project does not belong to your client account."
            )
            
    return project

# ----------------------------------------------------
# PROJECT MEMBERS
# ----------------------------------------------------
@router.post("/{project_id}/members", response_model=schemas.ProjectMemberOut, status_code=status.HTTP_201_CREATED)
def add_project_member(
    project_id: str,
    payload: schemas.ProjectMemberAdd,
    membership: models.AgencyMembership = Depends(auth.require_roles(["agency_admin"])),
    db: Session = Depends(get_db)
):
    # Verify project exists and belongs to active agency
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.agency_id == membership.agency_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found."
        )
        
    # Verify user being added is a member of the agency (cannot add external users)
    user_agency_membership = db.query(models.AgencyMembership).filter(
        models.AgencyMembership.user_id == payload.user_id,
        models.AgencyMembership.agency_id == membership.agency_id
    ).first()
    
    if not user_agency_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of this agency."
        )
        
    # Check if user is already a member of this project
    existing_project_member = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.user_id == payload.user_id
    ).first()
    
    if existing_project_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this project."
        )
        
    project_member = models.ProjectMember(
        project_id=project_id,
        user_id=payload.user_id
    )
    db.add(project_member)
    db.commit()
    db.refresh(project_member)
    return project_member

@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project_member(
    project_id: str,
    user_id: str,
    membership: models.AgencyMembership = Depends(auth.require_roles(["agency_admin"])),
    db: Session = Depends(get_db)
):
    # Verify project exists and belongs to active agency
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.agency_id == membership.agency_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found."
        )
        
    # Find project member record
    proj_member = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.user_id == user_id
    ).first()
    
    if not proj_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this project."
        )
        
    # Transactional execution of removing a project member:
    # 1. Unassign all their tasks within this specific project
    db.query(models.Task).filter(
        models.Task.assignee_id == user_id,
        models.Task.project_id == project_id
    ).update({models.Task.assignee_id: None}, synchronize_session=False)
    
    # 2. Delete the project member link
    db.delete(proj_member)
    db.commit()
    return

@router.get("/{project_id}/members", response_model=List[schemas.ProjectMemberOut])
def list_project_members(
    project_id: str,
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
    db: Session = Depends(get_db)
):
    # Verify project access
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.agency_id == membership.agency_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found."
        )
        
    # Role check
    if membership.role == "agency_member":
        is_member = db.query(models.ProjectMember).filter(
            models.ProjectMember.project_id == project_id,
            models.ProjectMember.user_id == membership.user_id
        ).first()
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this project's member list."
            )
    elif membership.role == "client_user":
        if project.client_id != membership.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: This project belongs to a different client."
            )
            
    members = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id
    ).all()
    return members
