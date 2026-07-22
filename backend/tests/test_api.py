import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db, current_user_id
from app import models, auth

# Setup a clean in-memory SQLite database for test runs
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override get_db dependency to use the test database
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Seed minimal baseline data for test assertions
    db = TestingSessionLocal()
    pass_hash = auth.get_password_hash("password123")
    
    # Users
    u1 = models.User(id="user_admin_a", email="admin.a@example.com", password_hash=pass_hash, full_name="Admin A")
    u2 = models.User(id="user_member_a", email="member.a@example.com", password_hash=pass_hash, full_name="Member A")
    u3 = models.User(id="user_client_a", email="client.a@example.com", password_hash=pass_hash, full_name="Client A")
    u4 = models.User(id="user_admin_b", email="admin.b@example.com", password_hash=pass_hash, full_name="Admin B")
    u_multi = models.User(id="user_multi", email="multi@example.com", password_hash=pass_hash, full_name="Multi User")
    
    db.add_all([u1, u2, u3, u4, u_multi])
    db.flush()
    
    # Agencies
    a1 = models.Agency(id="agency_a", name="Agency A", created_by=u1.id)
    a2 = models.Agency(id="agency_b", name="Agency B", created_by=u4.id)
    db.add_all([a1, a2])
    db.flush()
    
    # Clients
    c1 = models.Client(id="client_a1", agency_id="agency_a", name="Client A1", created_by=u1.id)
    db.add_all([c1])
    db.flush()
    
    # Memberships
    m1 = models.AgencyMembership(id="m1", user_id=u1.id, agency_id="agency_a", role="agency_admin")
    m2 = models.AgencyMembership(id="m2", user_id=u2.id, agency_id="agency_a", role="agency_member")
    m3 = models.AgencyMembership(id="m3", user_id=u3.id, agency_id="agency_a", role="client_user", client_id="client_a1")
    m4 = models.AgencyMembership(id="m4", user_id=u4.id, agency_id="agency_b", role="agency_admin")
    
    # Multi-agency memberships: Client in A, Member in B
    m_multi_a = models.AgencyMembership(id="m_multi_a", user_id=u_multi.id, agency_id="agency_a", role="client_user", client_id="client_a1")
    m_multi_b = models.AgencyMembership(id="m_multi_b", user_id=u_multi.id, agency_id="agency_b", role="agency_member")
    
    db.add_all([m1, m2, m3, m4, m_multi_a, m_multi_b])
    db.flush()
    
    # Projects
    p1 = models.Project(id="project_a1", agency_id="agency_a", client_id="client_a1", name="Project A1", created_by=u1.id)
    p2 = models.Project(id="project_b1", agency_id="agency_b", client_id="client_a1", name="Project B1", created_by=u4.id) # Wrong client but agency B
    db.add_all([p1, p2])
    db.flush()
    
    # Project Members
    pm1 = models.ProjectMember(project_id="project_a1", user_id=u2.id, created_by=u1.id)
    db.add_all([pm1])
    db.flush()
    
    # Tasks
    t1_visible = models.Task(
        id="task_visible", agency_id="agency_a", project_id="project_a1",
        title="Client Visible Task", is_client_visible=True, status="todo", created_by=u1.id
    )
    t2_internal = models.Task(
        id="task_internal", agency_id="agency_a", project_id="project_a1",
        title="Internal Task", is_client_visible=False, status="in_progress", assignee_id=u2.id, created_by=u1.id
    )
    db.add_all([t1_visible, t2_internal])
    db.flush()
    
    # Comments
    comm_vis = models.Comment(
        id="comment_vis", agency_id="agency_a", task_id="task_visible",
        user_id=u1.id, content="Visible Comment", is_client_visible=True, created_by=u1.id
    )
    comm_int = models.Comment(
        id="comment_int", agency_id="agency_a", task_id="task_visible",
        user_id=u1.id, content="Internal Comment", is_client_visible=False, created_by=u1.id
    )
    db.add_all([comm_vis, comm_int])
    db.flush()
    
    # Uploaded File
    file_vis = models.UploadedFile(
        id="file_vis", agency_id="agency_a", task_id="task_visible", user_id=u2.id,
        filename="design.png", file_path="mock_design.png", file_size=1024, is_client_visible=True,
        approval_status="pending", created_by=u2.id
    )
    file_int = models.UploadedFile(
        id="file_int", agency_id="agency_a", task_id="task_visible", user_id=u2.id,
        filename="key.json", file_path="mock_key.json", file_size=256, is_client_visible=False,
        approval_status="pending", created_by=u2.id
    )
    db.add_all([file_vis, file_int])
    
    db.commit()
    db.close()
    
    yield
    
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

def get_auth_headers(email: str) -> dict:
    response = client.post("/api/auth/login", data={"username": email, "password": "password123"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# ----------------------------------------------------
# 1. TEST TENANT ISOLATION
# ----------------------------------------------------
def test_cross_tenant_access_blocked():
    # Admin A attempts to access Project B1 from Agency B
    headers = get_auth_headers("admin.a@example.com")
    headers["X-Agency-ID"] = "agency_a" # Send valid session agency ID
    
    # Trying to query project details of project_b1 (from agency_b)
    # The API checks if the project belongs to the agency passed in X-Agency-ID.
    # Since project_b1 belongs to agency_b, it will not be found in agency_a, returning 404.
    response = client.get("/api/projects/project_b1", headers=headers)
    assert response.status_code == 404

    # Now if Admin A tries to forge the header to agency_b, the auth middleware will block them
    headers_forged = get_auth_headers("admin.a@example.com")
    headers_forged["X-Agency-ID"] = "agency_b"
    response = client.get("/api/projects/project_b1", headers=headers_forged)
    assert response.status_code == 403 # Forbidden (not a member of Agency B)

# ----------------------------------------------------
# 2. TEST CLIENT PORTAL VISIBILITY LIMITATIONS
# ----------------------------------------------------
def test_client_portal_leaks_prevented():
    headers = get_auth_headers("client.a@example.com")
    headers["X-Agency-ID"] = "agency_a"
    
    # Client A1 fetches tasks for Project A1.
    # Task List should return only the visible one.
    response = client.get("/api/tasks?project_id=project_a1", headers=headers)
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["id"] == "task_visible"
    
    # Directly requesting internal task details must be blocked
    response = client.get("/api/tasks/task_internal", headers=headers)
    assert response.status_code == 403
    
    # Requesting task comments for task_visible must exclude the internal comment
    response = client.get("/api/comments/task/task_visible", headers=headers)
    assert response.status_code == 200
    comments = response.json()
    assert len(comments) == 1
    assert comments[0]["id"] == "comment_vis"

    # Requesting task files for task_visible must exclude the internal file
    response = client.get("/api/files/task/task_visible", headers=headers)
    assert response.status_code == 200
    files = response.json()
    assert len(files) == 1
    assert files[0]["id"] == "file_vis"
    
    # Client cannot download internal file
    response = client.get("/api/files/file_int/download", headers=headers)
    assert response.status_code == 403

# ----------------------------------------------------
# 3. TEST ONE PERSON, TWO AGENCIES
# ----------------------------------------------------
def test_one_person_two_agencies():
    headers = get_auth_headers("multi@example.com")
    
    # Get profile details
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    profile = response.json()
    assert len(profile["memberships"]) == 2
    
    # Check roles
    memberships = {m["agency_id"]: m["role"] for m in profile["memberships"]}
    assert memberships["agency_a"] == "client_user"
    assert memberships["agency_b"] == "agency_member"
    
    # Try creating a task in Agency A (where user is client_user). Must be forbidden.
    headers["X-Agency-ID"] = "agency_a"
    task_payload = {"project_id": "project_a1", "title": "Client Forged Task"}
    response = client.post("/api/tasks", json=task_payload, headers=headers)
    assert response.status_code == 403
    
    # Mapped to Agency B, creating project/tasks or updating is authorized
    headers["X-Agency-ID"] = "agency_b"
    # User is agency_member in Agency B. Let's create a task in Project B1.
    # Note: the user must have project membership first. Let's add them as project member of B1.
    # We will log in as Admin B to do that.
    admin_b_headers = get_auth_headers("admin.b@example.com")
    admin_b_headers["X-Agency-ID"] = "agency_b"
    add_pm = client.post("/api/projects/project_b1/members", json={"user_id": "user_multi"}, headers=admin_b_headers)
    assert add_pm.status_code == 201
    
    # Now user_multi can create a task in project_b1
    task_payload_b = {"project_id": "project_b1", "title": "Multi Member Task"}
    response = client.post("/api/tasks", json=task_payload_b, headers=headers)
    assert response.status_code == 201

# ----------------------------------------------------
# 4. TEST INVITE RACES
# ----------------------------------------------------
def test_invite_races_and_resends():
    admin_headers = get_auth_headers("admin.a@example.com")
    admin_headers["X-Agency-ID"] = "agency_a"
    
    # Invite email
    payload = {"email": "new.invitee@example.com", "role": "agency_member"}
    
    # Send invite
    res1 = client.post("/api/invites", json=payload, headers=admin_headers)
    assert res1.status_code == 201
    token1 = res1.json()["token"]
    
    # Resend invite to same email. Unique constraint prevents duplicates, it updates the same row instead
    res2 = client.post("/api/invites", json=payload, headers=admin_headers)
    assert res2.status_code == 201
    token2 = res2.json()["token"]
    
    # Assert they are functionally the same row but token might have refreshed
    db = TestingSessionLocal()
    invites_in_db = db.query(models.Invitation).filter(models.Invitation.email == "new.invitee@example.com").all()
    assert len(invites_in_db) == 1
    db.close()

    # Accept the invite
    accept_payload = {"password": "password123", "full_name": "New Invitee"}
    res_accept1 = client.post(f"/api/invites/{token2}/accept", json=accept_payload)
    assert res_accept1.status_code == 200
    
    # Try accepting the invite again (accepted_at is now set)
    res_accept2 = client.post(f"/api/invites/{token2}/accept", json=accept_payload)
    assert res_accept2.status_code == 400
    assert "already been accepted" in res_accept2.json()["detail"]

# ----------------------------------------------------
# 5. TEST REMOVING TEAM MEMBER MID-TASK
# ----------------------------------------------------
def test_remove_team_member_mid_task():
    admin_headers = get_auth_headers("admin.a@example.com")
    admin_headers["X-Agency-ID"] = "agency_a"
    
    # Verify task_internal is assigned to member A (user_member_a)
    db = TestingSessionLocal()
    task = db.query(models.Task).filter(models.Task.id == "task_internal").first()
    assert task.assignee_id == "user_member_a"
    
    # Check project member exists
    proj_mem = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == "project_a1",
        models.ProjectMember.user_id == "user_member_a"
    ).first()
    assert proj_mem is not None
    db.close()
    
    # Remove member A from Agency A
    res_delete = client.delete("/api/agencies/members/user_member_a", headers=admin_headers)
    assert res_delete.status_code == 204
    
    # Assert that:
    # 1. Membership is deleted
    # 2. ProjectMember link is deleted
    # 3. task_internal.assignee_id is set to None (unassigned)
    db = TestingSessionLocal()
    membership = db.query(models.AgencyMembership).filter(
        models.AgencyMembership.user_id == "user_member_a",
        models.AgencyMembership.agency_id == "agency_a"
    ).first()
    assert membership is None
    
    proj_mem_after = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == "project_a1",
        models.ProjectMember.user_id == "user_member_a"
    ).first()
    assert proj_mem_after is None
    
    task_after = db.query(models.Task).filter(models.Task.id == "task_internal").first()
    assert task_after.assignee_id is None
    db.close()

# ----------------------------------------------------
# 6. TEST AUTOMATED AUDIT TRAIL
# ----------------------------------------------------
def test_automated_audit_trail():
    headers = get_auth_headers("admin.a@example.com")
    headers["X-Agency-ID"] = "agency_a"
    
    # Post a comment as Admin A (user_admin_a)
    payload = {"content": "Audit check comment", "is_client_visible": True}
    response = client.post("/api/comments?task_id=task_visible", json=payload, headers=headers)
    assert response.status_code == 201
    comment_data = response.json()
    
    # Verify that created_by was automatically set to user_admin_a by the db event listener
    assert comment_data["created_by"] == "user_admin_a"
    assert comment_data["updated_by"] == "user_admin_a"
    assert comment_data["created_at"] is not None
    assert comment_data["updated_at"] is not None
