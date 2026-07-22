from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

# ----------------------------------------------------
# USER SCHEMAS
# ----------------------------------------------------
class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------------------------------------------
# AGENCY SCHEMAS
# ----------------------------------------------------
class AgencyBase(BaseModel):
    name: str

class AgencyCreate(AgencyBase):
    pass

class AgencyOut(AgencyBase):
    id: str
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------------------------------------------
# CLIENT SCHEMAS
# ----------------------------------------------------
class ClientBase(BaseModel):
    name: str

class ClientCreate(ClientBase):
    pass

class ClientOut(ClientBase):
    id: str
    agency_id: str
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------------------------------------------
# AGENCY MEMBERSHIP SCHEMAS
# ----------------------------------------------------
class MembershipOut(BaseModel):
    id: str
    user: UserOut
    agency_id: str
    client_id: Optional[str] = None
    role: str
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SwitchAgencyRequest(BaseModel):
    agency_id: str

# ----------------------------------------------------
# PROJECT SCHEMAS
# ----------------------------------------------------
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    client_id: str

class ProjectOut(ProjectBase):
    id: str
    agency_id: str
    client_id: str
    client: ClientOut
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProjectMemberAdd(BaseModel):
    user_id: str

class ProjectMemberOut(BaseModel):
    id: str
    project_id: str
    user: UserOut
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------------------------------------------
# TASK SCHEMAS
# ----------------------------------------------------
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "todo" # todo, in_progress, in_review, completed
    priority: str = "medium" # low, medium, high, urgent
    assignee_id: Optional[str] = None
    due_date: Optional[datetime] = None
    start_date: Optional[date] = None
    parent_task_id: Optional[str] = None
    is_client_visible: bool = False

class TaskCreate(TaskBase):
    project_id: str

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[str] = None
    due_date: Optional[datetime] = None
    start_date: Optional[date] = None
    parent_task_id: Optional[str] = None
    is_client_visible: Optional[bool] = None

class TaskOut(TaskBase):
    id: str
    agency_id: str
    project_id: str
    assignee: Optional[UserOut] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------------------------------------------
# TIME ENTRY SCHEMAS
# ----------------------------------------------------
class TimeEntryCreate(BaseModel):
    duration_minutes: int
    note: Optional[str] = None
    date: date

class TimeEntryOut(BaseModel):
    id: str
    agency_id: str
    task_id: str
    user_id: str
    duration_minutes: int
    note: Optional[str] = None
    date: date
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------------------------------------------
# COMMENT SCHEMAS
# ----------------------------------------------------
class CommentCreate(BaseModel):
    content: str
    is_client_visible: bool = False

class CommentOut(BaseModel):
    id: str
    agency_id: str
    task_id: str
    user_id: str
    content: str
    is_client_visible: bool
    author: UserOut
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------------------------------------------
# FILE SCHEMAS
# ----------------------------------------------------
class FileApprovalUpdate(BaseModel):
    approval_status: str # approved, changes_requested

class FileOut(BaseModel):
    id: str
    agency_id: str
    task_id: str
    user_id: str
    filename: str
    file_path: str
    mime_type: Optional[str] = None
    file_size: int
    is_client_visible: bool
    approval_status: str
    uploader: UserOut
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------------------------------------------
# INVITATION SCHEMAS
# ----------------------------------------------------
class InvitationCreate(BaseModel):
    email: EmailStr
    role: str # agency_admin, agency_member, client_user
    client_id: Optional[str] = None

class InvitationOut(BaseModel):
    id: str
    agency_id: str
    client_id: Optional[str] = None
    email: EmailStr
    role: str
    token: str
    accepted_at: Optional[datetime] = None
    expires_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class InviteAccept(BaseModel):
    password: str
    full_name: str

class InviteDetailsOut(BaseModel):
    agency_name: str
    email: EmailStr
    role: str
    client_name: Optional[str] = None

# ----------------------------------------------------
# DASHBOARD SCHEMAS
# ----------------------------------------------------
class ProjectDashboardMetrics(BaseModel):
    total_tasks: int
    todo_tasks: int
    in_progress_tasks: int
    in_review_tasks: int
    completed_tasks: int
    total_hours_logged: float

# ----------------------------------------------------
# NOTIFICATION SCHEMAS
# ----------------------------------------------------
class NotificationOut(BaseModel):
    id: str
    agency_id: str
    user_id: str
    event_type: str
    title: str
    message: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    is_read: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ----------------------------------------------------
# CLIENT INTAKE FORM SCHEMAS
# ----------------------------------------------------
class ClientIntakeFormCreate(BaseModel):
    title: str
    fields_schema: dict = Field(default_factory=dict)
    is_active: bool = True


class ClientIntakeFormOut(BaseModel):
    id: str
    agency_id: str
    title: str
    fields_schema: dict
    share_token: str
    is_active: bool
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClientIntakeSubmissionCreate(BaseModel):
    client_name: str
    project_name: str
    project_description: Optional[str] = None
    answers: dict = Field(default_factory=dict)


class ClientIntakeSubmissionOut(BaseModel):
    id: str
    agency_id: str
    form_id: str
    client_id: str
    project_id: str
    client_name: str
    project_name: str
    answers_json: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
