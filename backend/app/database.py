import os
import datetime
from contextvars import ContextVar
from typing import Generator, Optional
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

# Context variable to store the authenticated user ID for the current request
# This allows audit event listeners to automatically populate created_by and updated_by.
current_user_id: ContextVar[Optional[str]] = ContextVar("current_user_id", default=None)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agencydesk.db")

# SQLite needs special arguments to enable foreign keys and concurrent thread access
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
    # Enable foreign keys in SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    engine = create_engine(DATABASE_URL)

from sqlalchemy.orm import declarative_base, sessionmaker, object_session

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ORM Event Listeners for Audit Columns
@event.listens_for(Base, "before_insert", propagate=True)
def before_insert_listener(mapper, connection, target):
    session = object_session(target)
    user_id = None
    if session and "current_user_id" in session.info:
        user_id = session.info["current_user_id"]
    if not user_id:
        user_id = current_user_id.get()
        
    now = datetime.datetime.utcnow()
    
    if hasattr(target, "created_at") and getattr(target, "created_at") is None:
        target.created_at = now
    if hasattr(target, "updated_at") and getattr(target, "updated_at") is None:
        target.updated_at = now
        
    # Set audit user fields if they are defined on the model
    if hasattr(target, "created_by") and getattr(target, "created_by") is None:
        if user_id:
            target.created_by = user_id
    if hasattr(target, "updated_by") and getattr(target, "updated_by") is None:
        if user_id:
            target.updated_by = user_id

@event.listens_for(Base, "before_update", propagate=True)
def before_update_listener(mapper, connection, target):
    session = object_session(target)
    user_id = None
    if session and "current_user_id" in session.info:
        user_id = session.info["current_user_id"]
    if not user_id:
        user_id = current_user_id.get()
        
    now = datetime.datetime.utcnow()
    
    if hasattr(target, "updated_at"):
        target.updated_at = now
        
    if hasattr(target, "updated_by"):
        if user_id:
            target.updated_by = user_id

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
