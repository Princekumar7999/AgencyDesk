from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from .. import models, schemas, auth

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/project/{project_id}", response_model=schemas.ProjectDashboardMetrics)
def get_project_dashboard(
    project_id: str,
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
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
        
    # Role checks
    if membership.role == "agency_member":
        is_member = db.query(models.ProjectMember).filter(
            models.ProjectMember.project_id == project_id,
            models.ProjectMember.user_id == membership.user_id
        ).first()
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this project's dashboard."
            )
    elif membership.role == "client_user":
        if project.client_id != membership.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: This project belongs to a different client."
            )
            
    # Subqueries for tasks metrics
    task_query = db.query(models.Task).filter(
        models.Task.project_id == project_id,
        models.Task.agency_id == membership.agency_id
    )
    
    time_query = db.query(func.sum(models.TimeEntry.duration_minutes)).join(
        models.Task, models.Task.id == models.TimeEntry.task_id
    ).filter(
        models.Task.project_id == project_id,
        models.Task.agency_id == membership.agency_id
    )
    
    # Apply Client Scoping Filters: Clients only see client-visible data
    if membership.role == "client_user":
        task_query = task_query.filter(models.Task.is_client_visible == True)
        time_query = time_query.filter(models.Task.is_client_visible == True)
        
    tasks = task_query.all()
    total_minutes = time_query.scalar() or 0
    total_hours = round(total_minutes / 60.0, 2)
    
    # Calculate counts by status
    total_tasks = len(tasks)
    todo = sum(1 for t in tasks if t.status == "todo")
    in_progress = sum(1 for t in tasks if t.status == "in_progress")
    in_review = sum(1 for t in tasks if t.status == "in_review")
    completed = sum(1 for t in tasks if t.status == "completed")
    
    return {
        "total_tasks": total_tasks,
        "todo_tasks": todo,
        "in_progress_tasks": in_progress,
        "in_review_tasks": in_review,
        "completed_tasks": completed,
        "total_hours_logged": total_hours
    }
