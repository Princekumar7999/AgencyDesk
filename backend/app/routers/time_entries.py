from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from .. import models, schemas, auth

router = APIRouter(prefix="/time-entries", tags=["Time Tracking"])

def get_authorized_task(task_id: str, membership: models.AgencyMembership, db: Session) -> models.Task:
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.agency_id == membership.agency_id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found."
        )
        
    # Check project access
    project = db.query(models.Project).filter(
        models.Project.id == task.project_id,
        models.Project.agency_id == membership.agency_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found."
        )
        
    if membership.role == "agency_member":
        is_member = db.query(models.ProjectMember).filter(
            models.ProjectMember.project_id == project.id,
            models.ProjectMember.user_id == membership.user_id
        ).first()
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this project's tasks."
            )
    elif membership.role == "client_user":
        if project.client_id != membership.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: This project does not belong to your client account."
            )
        if not task.is_client_visible:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: This task is internal only."
            )
            
    return task

@router.post("", response_model=schemas.TimeEntryOut, status_code=status.HTTP_201_CREATED)
def log_time(
    payload: schemas.TimeEntryCreate,
    task_id: str,
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
    db: Session = Depends(get_db)
):
    if membership.role == "client_user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clients are not allowed to log time."
        )
        
    # Verify task access
    task = get_authorized_task(task_id, membership, db)
    
    time_entry = models.TimeEntry(
        agency_id=membership.agency_id,
        task_id=task_id,
        user_id=membership.user_id,
        duration_minutes=payload.duration_minutes,
        note=payload.note,
        date=payload.date
    )
    db.add(time_entry)
    db.commit()
    db.refresh(time_entry)
    return time_entry

@router.get("/project/{project_id}/summary")
def get_project_hours_summary(
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
        
    if membership.role == "agency_member":
        is_member = db.query(models.ProjectMember).filter(
            models.ProjectMember.project_id == project_id,
            models.ProjectMember.user_id == membership.user_id
        ).first()
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this project."
            )
    elif membership.role == "client_user":
        if project.client_id != membership.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: This project does not belong to your client."
            )
            
    # Calculate sum of time entry durations (in minutes) for tasks in this project
    # Clients are only allowed to see cumulative hours, but we scope the query appropriately.
    # Note: Does a client user see hours on internal tasks?
    # Spec: "Dashboards & reporting: scoped to what the viewer is allowed to see."
    # If the viewer is a client, we must ONLY sum hours logged against tasks that are client visible!
    # If the viewer is agency staff, we sum all hours.
    
    query = db.query(func.sum(models.TimeEntry.duration_minutes)).join(
        models.Task, models.Task.id == models.TimeEntry.task_id
    ).filter(
        models.Task.project_id == project_id,
        models.Task.agency_id == membership.agency_id
    )
    
    if membership.role == "client_user":
        # Only sum time entries for client visible tasks
        query = query.filter(models.Task.is_client_visible == True)
        
    total_minutes = query.scalar() or 0
    total_hours = round(total_minutes / 60.0, 2)
    
    return {
        "project_id": project_id,
        "total_minutes": total_minutes,
        "total_hours": total_hours
    }

@router.get("/task/{task_id}", response_model=List[schemas.TimeEntryOut])
def get_task_time_entries(
    task_id: str,
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
    db: Session = Depends(get_db)
):
    # Detailed granular log entries are internal to agency only
    if membership.role == "client_user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Detailed time logs are internal and not visible to clients."
        )
        
    # Verify task exists and is in the active agency
    task = get_authorized_task(task_id, membership, db)
    
    entries = db.query(models.TimeEntry).filter(
        models.TimeEntry.task_id == task_id,
        models.TimeEntry.agency_id == membership.agency_id
    ).all()
    
    return entries
