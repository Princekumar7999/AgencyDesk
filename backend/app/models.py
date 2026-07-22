import uuid
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Date, Text, UniqueConstraint, Index, text
from sqlalchemy.orm import relationship
from .database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Relationships
    memberships = relationship("AgencyMembership", back_populates="user", cascade="all, delete-orphan", foreign_keys="[AgencyMembership.user_id]")
    assigned_tasks = relationship("Task", back_populates="assignee", foreign_keys="[Task.assignee_id]")
    project_memberships = relationship("ProjectMember", back_populates="user", cascade="all, delete-orphan", foreign_keys="[ProjectMember.user_id]")


class Agency(Base):
    __tablename__ = "agencies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    
    # Audit fields
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Relationships
    memberships = relationship("AgencyMembership", back_populates="agency", cascade="all, delete-orphan")
    clients = relationship("Client", back_populates="agency", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="agency", cascade="all, delete-orphan")
    invitations = relationship("Invitation", back_populates="agency", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="agency", cascade="all, delete-orphan")
    intake_forms = relationship("ClientIntakeForm", back_populates="agency", cascade="all, delete-orphan")


class Client(Base):
    __tablename__ = "clients"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    agency_id = Column(String(36), ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)

    # Audit fields
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Relationships
    agency = relationship("Agency", back_populates="clients")
    projects = relationship("Project", back_populates="client", cascade="all, delete-orphan")
    memberships = relationship("AgencyMembership", back_populates="client")

# Index for multi-tenant query performance
Index("idx_clients_agency_id", Client.agency_id)


class AgencyMembership(Base):
    __tablename__ = "agency_memberships"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    agency_id = Column(String(36), ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    role = Column(String(50), nullable=False) # agency_admin, agency_member, client_user

    # Audit fields
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Relationships
    user = relationship("User", back_populates="memberships", foreign_keys=[user_id])
    agency = relationship("Agency", back_populates="memberships")
    client = relationship("Client", back_populates="memberships")

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "agency_id", name="uq_user_agency"),
        Index("idx_membership_user_agency", "user_id", "agency_id"),
        Index("idx_membership_agency_id", "agency_id"),
        Index("idx_membership_client_id", "client_id"),
    )


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    agency_id = Column(String(36), ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)

    # Audit fields
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Relationships
    agency = relationship("Agency", back_populates="projects")
    client = relationship("Client", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_projects_agency_id", "agency_id"),
        Index("idx_projects_client_id", "client_id"),
    )


class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Audit fields
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_memberships", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_user"),
        Index("idx_proj_member_project_id", "project_id"),
        Index("idx_proj_member_user_id", "user_id"),
    )


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    agency_id = Column(String(36), ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String(2000), nullable=True)
    status = Column(String(50), nullable=False, default="todo") # todo, in_progress, in_review, completed
    priority = Column(String(50), nullable=False, default="medium") # low, medium, high, urgent
    assignee_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    due_date = Column(DateTime, nullable=True)
    
    # Gantt / Timeline extension points
    start_date = Column(Date, nullable=True)
    parent_task_id = Column(String(36), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    
    is_client_visible = Column(Boolean, default=False, nullable=False)

    # Audit fields
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", back_populates="assigned_tasks", foreign_keys=[assignee_id])
    time_entries = relationship("TimeEntry", back_populates="task", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")
    files = relationship("UploadedFile", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_tasks_agency_id", "agency_id"),
        Index("idx_tasks_project_id", "project_id"),
        Index("idx_tasks_assignee_id", "assignee_id"),
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_agency_status", "agency_id", "status"),
        Index("idx_tasks_project_client_visibility", "project_id", "is_client_visible"),
    )


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    agency_id = Column(String(36), ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    note = Column(String(1000), nullable=True)
    date = Column(Date, nullable=False)

    # Audit fields
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Relationships
    task = relationship("Task", back_populates="time_entries")

    __table_args__ = (
        Index("idx_time_agency_id", "agency_id"),
        Index("idx_time_task_id", "task_id"),
        Index("idx_time_user_id", "user_id"),
    )


class Comment(Base):
    __tablename__ = "comments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    agency_id = Column(String(36), ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(String(2000), nullable=False)
    is_client_visible = Column(Boolean, default=False, nullable=False)

    # Audit fields
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Relationships
    task = relationship("Task", back_populates="comments")
    author = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("idx_comments_agency_id", "agency_id"),
        Index("idx_comments_task_id", "task_id"),
        Index("idx_comments_user_id", "user_id"),
        Index("idx_comments_task_visibility", "task_id", "is_client_visible"),
    )


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    agency_id = Column(String(36), ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=False)
    is_client_visible = Column(Boolean, default=False, nullable=False)
    approval_status = Column(String(50), nullable=False, default="pending") # pending, approved, changes_requested

    # Audit fields
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Relationships
    task = relationship("Task", back_populates="files")
    uploader = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("idx_files_agency_id", "agency_id"),
        Index("idx_files_task_id", "task_id"),
        Index("idx_files_user_id", "user_id"),
        Index("idx_files_task_visibility", "task_id", "is_client_visible"),
    )


class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    agency_id = Column(String(36), ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    email = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False) # agency_admin, agency_member, client_user
    token = Column(String(255), unique=True, nullable=False, index=True)
    accepted_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)

    # Audit fields
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Relationships
    agency = relationship("Agency", back_populates="invitations")
    client = relationship("Client")

    __table_args__ = (
        Index("idx_invites_agency_id", "agency_id"),
        Index("idx_invites_client_id", "client_id"),
        # Partial unique index to enforce "one pending invite per email per agency at a time"
        Index(
            "idx_invites_pending_agency_email",
            "agency_id",
            "email",
            unique=True,
            sqlite_where=text("accepted_at IS NULL"),
            postgresql_where=text("accepted_at IS NULL")
        )
    )


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    agency_id = Column(String(36), ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(String(2000), nullable=False)
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(String(36), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)

    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    agency = relationship("Agency", back_populates="notifications")
    recipient = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("idx_notifications_agency_id", "agency_id"),
        Index("idx_notifications_user_id", "user_id"),
        Index("idx_notifications_read", "user_id", "is_read"),
    )


class ClientIntakeForm(Base):
    __tablename__ = "client_intake_forms"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    agency_id = Column(String(36), ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    fields_schema = Column(Text, nullable=False)
    share_token = Column(String(255), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    agency = relationship("Agency", back_populates="intake_forms")
    submissions = relationship("ClientIntakeSubmission", back_populates="form", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_intake_forms_agency_id", "agency_id"),
    )


class ClientIntakeSubmission(Base):
    __tablename__ = "client_intake_submissions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    agency_id = Column(String(36), ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    form_id = Column(String(36), ForeignKey("client_intake_forms.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    client_name = Column(String(255), nullable=False)
    project_name = Column(String(255), nullable=False)
    answers_json = Column(Text, nullable=False)

    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    form = relationship("ClientIntakeForm", back_populates="submissions")

    __table_args__ = (
        Index("idx_intake_submissions_agency_id", "agency_id"),
        Index("idx_intake_submissions_form_id", "form_id"),
    )
