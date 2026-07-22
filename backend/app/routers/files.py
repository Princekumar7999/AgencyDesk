import os
import shutil
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas, auth

router = APIRouter(prefix="/files", tags=["Files"])

# Ensure uploads directory exists inside the workspace backend folder
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
                detail="You do not have access to this project."
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

@router.post("", response_model=schemas.FileOut, status_code=status.HTTP_201_CREATED)
def upload_file(
    task_id: str = Form(...),
    is_client_visible: bool = Form(False),
    file: UploadFile = File(...),
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
    db: Session = Depends(get_db)
):
    # Verify task access
    task = get_authorized_task(task_id, membership, db)
    
    # Client visibility checks
    visible = is_client_visible
    if membership.role == "client_user":
        visible = True # Clients uploads are visible
        
    # Generate unique filename on disk to prevent overwriting
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_dest_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save the file bytes
    try:
        with open(file_dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
        
    # Calculate file size
    file_size = os.path.getsize(file_dest_path)
    
    # Register file in DB
    uploaded_file = models.UploadedFile(
        agency_id=membership.agency_id,
        task_id=task_id,
        user_id=membership.user_id,
        filename=file.filename,
        file_path=unique_filename,
        mime_type=file.content_type,
        file_size=file_size,
        is_client_visible=visible,
        approval_status="pending"
    )
    db.add(uploaded_file)
    db.commit()
    db.refresh(uploaded_file)
    
    return db.query(models.UploadedFile).filter(models.UploadedFile.id == uploaded_file.id).first()

@router.get("/task/{task_id}", response_model=List[schemas.FileOut])
def list_task_files(
    task_id: str,
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
    db: Session = Depends(get_db)
):
    task = get_authorized_task(task_id, membership, db)
    
    query = db.query(models.UploadedFile).filter(
        models.UploadedFile.task_id == task_id,
        models.UploadedFile.agency_id == membership.agency_id
    )
    
    if membership.role == "client_user":
        query = query.filter(models.UploadedFile.is_client_visible == True)
        
    files = query.order_by(models.UploadedFile.created_at.desc()).all()
    return files

@router.get("/{file_id}/download")
def download_file(
    file_id: str,
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
    db: Session = Depends(get_db)
):
    uploaded_file = db.query(models.UploadedFile).filter(
        models.UploadedFile.id == file_id,
        models.UploadedFile.agency_id == membership.agency_id
    ).first()
    
    if not uploaded_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found."
        )
        
    # Validate task/project permissions
    get_authorized_task(uploaded_file.task_id, membership, db)
    
    # Client visibility leak check
    if membership.role == "client_user" and not uploaded_file.is_client_visible:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: This file is internal only."
        )
        
    file_full_path = os.path.join(UPLOAD_DIR, uploaded_file.file_path)
    if not os.path.exists(file_full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File physical attachment not found on disk."
        )
        
    return FileResponse(
        path=file_full_path,
        filename=uploaded_file.filename,
        media_type=uploaded_file.mime_type
    )

@router.put("/{file_id}/approval", response_model=schemas.FileOut)
def update_file_approval(
    file_id: str,
    payload: schemas.FileApprovalUpdate,
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
    db: Session = Depends(get_db)
):
    # Only client_user and agency staff can access. Client users can mark files approved or needs changes.
    uploaded_file = db.query(models.UploadedFile).filter(
        models.UploadedFile.id == file_id,
        models.UploadedFile.agency_id == membership.agency_id
    ).first()
    
    if not uploaded_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found."
        )
        
    # Verify task/project access
    get_authorized_task(uploaded_file.task_id, membership, db)
    
    # If client, make sure they only approve client-visible files
    if membership.role == "client_user" and not uploaded_file.is_client_visible:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: This file is internal only."
        )
        
    # Validate payload value
    status_val = payload.approval_status
    if status_val not in ["approved", "changes_requested", "pending"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Allowed values: approved, changes_requested, pending."
        )
        
    # Update status
    uploaded_file.approval_status = status_val
    db.commit()
    db.refresh(uploaded_file)
    return uploaded_file
