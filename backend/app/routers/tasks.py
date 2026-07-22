from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas, auth

router = APIRouter(prefix="/tasks", tags=["Tasks"])

def check_project_access(project_id: str, membership: models.AgencyMembership, db: Session) -> models.Project:
    # Fetch project and ensure it belongs to active agency (Tenant Isolation)
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.agency_id == membership.agency_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found."
        )
        
    # Role-based check
    if membership.role == "agency_member":
        is_member = db.query(models.ProjectMember).filter(
            models.ProjectMember.project_id == project_id,
            models.ProjectMember.user_id == membership.user_id
        ).first()
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this project."
            )
    elif membership.role == "client_user":
        if project.client_id != membership.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: This project does not belong to your client account."
            )
            
    return project

@router.post("", response_model=schemas.TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: schemas.TaskCreate,
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
    db: Session = Depends(get_db)
):
    if membership.role == "client_user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clients are not allowed to create tasks."
        )
        
    # Ensure they have access to the target project
    project = check_project_access(payload.project_id, membership, db)
    
    # Verify assignee is member of agency
    if payload.assignee_id:
        assignee_membership = db.query(models.AgencyMembership).filter(
            models.AgencyMembership.user_id == payload.assignee_id,
            models.AgencyMembership.agency_id == membership.agency_id
        ).first()
        if not assignee_membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignee is not a member of this agency."
            )
            
    # Create Task
    task = models.Task(
        agency_id=membership.agency_id,
        project_id=payload.project_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        assignee_id=payload.assignee_id,
        due_date=payload.due_date,
        start_date=payload.start_date,
        parent_task_id=payload.parent_task_id,
        is_client_visible=payload.is_client_visible
    )
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Reload with relations
    return db.query(models.Task).filter(models.Task.id == task.id).first()

@router.get("", response_model=List[schemas.TaskOut])
def list_tasks(
    project_id: str,
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
    db: Session = Depends(get_db)
):
    # Ensure user has access to the project
    project = check_project_access(project_id, membership, db)
    
    query = db.query(models.Task).filter(
        models.Task.project_id == project_id,
        models.Task.agency_id == membership.agency_id
    )
    
    # Clients see only client-visible tasks
    if membership.role == "client_user":
        query = query.filter(models.Task.is_client_visible == True)
        
    return query.all()

@router.get("/{task_id}", response_model=schemas.TaskOut)
def get_task(
    task_id: str,
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
    db: Session = Depends(get_db)
):
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.agency_id == membership.agency_id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found."
        )
        
    # Verify project access
    check_project_access(task.project_id, membership, db)
    
    # Check client visibility leak
    if membership.role == "client_user" and not task.is_client_visible:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: This task is internal only."
        )
        
    return task

@router.put("/{task_id}", response_model=schemas.TaskOut)
def update_task(
    task_id: str,
    payload: schemas.TaskUpdate,
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
    db: Session = Depends(get_db)
):
    if membership.role == "client_user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clients are not allowed to modify task details."
        )
        
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.agency_id == membership.agency_id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found."
        )
        
    # Ensure they have access to this project
    check_project_access(task.project_id, membership, db)
    
    # Handle optional update fields
    update_data = payload.dict(exclude_unset=True)
    
    # Verify assignee if updated
    if "assignee_id" in update_data and update_data["assignee_id"] is not None:
        assignee_membership = db.query(models.AgencyMembership).filter(
            models.AgencyMembership.user_id == update_data["assignee_id"],
            models.AgencyMembership.agency_id == membership.agency_id
        ).first()
        if not assignee_membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignee is not a member of this agency."
            )
            
    for key, value in update_data.items():
        setattr(task, key, value)
        
    db.commit()
    db.refresh(task)
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: str,
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
    db: Session = Depends(get_db)
):
    if membership.role == "client_user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clients are not allowed to delete tasks."
        )
        
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.agency_id == membership.agency_id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found."
        )
        
    # Ensure they have access to this project
    check_project_access(task.project_id, membership, db)
    
    db.delete(task)
    db.commit()
    return
