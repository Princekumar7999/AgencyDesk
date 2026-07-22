from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas, auth

router = APIRouter(prefix="/comments", tags=["Comments"])

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
        
    # Verify project access
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
                detail="Access Denied: This project does not belong to your client."
            )
        if not task.is_client_visible:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: This task is internal only."
            )
            
    return task

@router.post("", response_model=schemas.CommentOut, status_code=status.HTTP_201_CREATED)
def create_comment(
    payload: schemas.CommentCreate,
    task_id: str,
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
    db: Session = Depends(get_db)
):
    # Verify task access
    task = get_authorized_task(task_id, membership, db)
    
    # Client visibility business rules:
    # 1. Clients cannot write internal agency notes.
    # 2. Clients cannot comment on internal tasks (prevented in get_authorized_task).
    is_visible = payload.is_client_visible
    if membership.role == "client_user":
        is_visible = True # Force client-posted comments to be client-visible
        
    comment = models.Comment(
        agency_id=membership.agency_id,
        task_id=task_id,
        user_id=membership.user_id,
        content=payload.content,
        is_client_visible=is_visible
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    # Reload with author relation
    return db.query(models.Comment).filter(models.Comment.id == comment.id).first()

@router.get("/task/{task_id}", response_model=List[schemas.CommentOut])
def list_task_comments(
    task_id: str,
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
    db: Session = Depends(get_db)
):
    # Verify task access
    task = get_authorized_task(task_id, membership, db)
    
    query = db.query(models.Comment).filter(
        models.Comment.task_id == task_id,
        models.Comment.agency_id == membership.agency_id
    )
    
    # Client portal filters comments:
    # Client users see ONLY client-visible comments.
    # Agency staff see ALL comments (internal + client-visible).
    if membership.role == "client_user":
        query = query.filter(models.Comment.is_client_visible == True)
        
    # Sort comments oldest to newest
    comments = query.order_by(models.Comment.created_at.asc()).all()
    return comments
