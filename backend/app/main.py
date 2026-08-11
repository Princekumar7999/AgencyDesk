from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .routers import auth, agencies, projects, tasks, time_entries, comments, files, invites, dashboard, notifications, intake_forms

# Automatically create tables in SQLite/relational database on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AgencyDesk API",
    description="Multi-tenant agency & client project management portal API",
    version="1.0.0"
)




# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://agency-desk-iota.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix="/api")
app.include_router(agencies.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(time_entries.router, prefix="/api")
app.include_router(comments.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(invites.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(intake_forms.router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "app": "AgencyDesk Multi-Tenant API",
        "documentation": "/docs"
    }
