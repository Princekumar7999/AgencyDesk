import datetime
from app import models, auth
from app.database import SessionLocal, Base, engine, current_user_id

def seed_db():
    # Recreate tables to start clean
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("Seeding database...")

        # ----------------------------------------------------
        # 1. CREATE USERS
        # ----------------------------------------------------
        pass_hash = auth.get_password_hash("password123")

        u_apex_admin = models.User(email="admin.apex@example.com", password_hash=pass_hash, full_name="Alice Admin (Apex)")
        u_apex_member = models.User(email="member.apex@example.com", password_hash=pass_hash, full_name="Bob Member (Apex)")
        u_apex_client = models.User(email="client.apex@example.com", password_hash=pass_hash, full_name="Charlie Client (Apex)")
        
        u_quantum_admin = models.User(email="admin.quantum@example.com", password_hash=pass_hash, full_name="Quincy Admin (Quantum)")
        u_quantum_client = models.User(email="client.quantum@example.com", password_hash=pass_hash, full_name="Quinn Client (Quantum)")
        
        # User mapped to multiple agencies: client in Apex, member in Quantum
        u_multi = models.User(email="multi.user@example.com", password_hash=pass_hash, full_name="Morgan Multi")

        db.add_all([u_apex_admin, u_apex_member, u_apex_client, u_quantum_admin, u_quantum_client, u_multi])
        db.flush()

        # ----------------------------------------------------
        # 2. CREATE AGENCIES
        # ----------------------------------------------------
        agency_apex = models.Agency(name="Apex Digital", created_by=u_apex_admin.id)
        agency_quantum = models.Agency(name="Quantum Labs", created_by=u_quantum_admin.id)
        db.add_all([agency_apex, agency_quantum])
        db.flush()

        # Set audit context to Apex Admin for creation
        current_user_id.set(u_apex_admin.id)

        # ----------------------------------------------------
        # 3. CREATE CLIENTS
        # ----------------------------------------------------
        client_alpha = models.Client(agency_id=agency_apex.id, name="Alpha Corp")
        client_beta = models.Client(agency_id=agency_quantum.id, name="Beta Industries")
        db.add_all([client_alpha, client_beta])
        db.flush()

        # ----------------------------------------------------
        # 4. AGENCY MEMBERSHIPS
        # ----------------------------------------------------
        # Apex Memberships
        m_apex_admin = models.AgencyMembership(user_id=u_apex_admin.id, agency_id=agency_apex.id, role="agency_admin")
        m_apex_member = models.AgencyMembership(user_id=u_apex_member.id, agency_id=agency_apex.id, role="agency_member")
        m_apex_client = models.AgencyMembership(user_id=u_apex_client.id, agency_id=agency_apex.id, role="client_user", client_id=client_alpha.id)
        
        # Quantum Memberships
        m_quantum_admin = models.AgencyMembership(user_id=u_quantum_admin.id, agency_id=agency_quantum.id, role="agency_admin")
        m_quantum_client = models.AgencyMembership(user_id=u_quantum_client.id, agency_id=agency_quantum.id, role="client_user", client_id=client_beta.id)
        
        # Multi-agency User memberships:
        # Charlie is client user for Alpha Corp in Apex Digital
        # Morgan (multi.user@example.com) is client user for Alpha Corp in Apex Digital
        m_multi_apex = models.AgencyMembership(user_id=u_multi.id, agency_id=agency_apex.id, role="client_user", client_id=client_alpha.id)
        # Morgan is also agency member (developer) in Quantum Labs
        m_multi_quantum = models.AgencyMembership(user_id=u_multi.id, agency_id=agency_quantum.id, role="agency_member")

        db.add_all([
            m_apex_admin, m_apex_member, m_apex_client, 
            m_quantum_admin, m_quantum_client, 
            m_multi_apex, m_multi_quantum
        ])
        db.flush()

        # ----------------------------------------------------
        # 5. PROJECTS
        # ----------------------------------------------------
        # Apex Projects
        proj_website = models.Project(agency_id=agency_apex.id, client_id=client_alpha.id, name="Alpha Website Redesign", description="Rebuilding Alpha Corp's main landing website on Next.js")
        proj_branding = models.Project(agency_id=agency_apex.id, client_id=client_alpha.id, name="Alpha Brand Identity", description="Developing a clean modern brand book and color palettes")
        
        # Quantum Projects
        proj_seo = models.Project(agency_id=agency_quantum.id, client_id=client_beta.id, name="Beta SEO Campaign", description="Optimizing SEO metrics and generating quarterly organic search reports")

        db.add_all([proj_website, proj_branding, proj_seo])
        db.flush()

        # ----------------------------------------------------
        # 6. PROJECT MEMBERS
        # ----------------------------------------------------
        # Apex website project members: Admin and Member
        pm1 = models.ProjectMember(project_id=proj_website.id, user_id=u_apex_admin.id)
        pm2 = models.ProjectMember(project_id=proj_website.id, user_id=u_apex_member.id)
        # Branding project only has Admin
        pm3 = models.ProjectMember(project_id=proj_branding.id, user_id=u_apex_admin.id)

        # Quantum project member: Quinn and Morgan Multi
        pm_q1 = models.ProjectMember(project_id=proj_seo.id, user_id=u_quantum_admin.id)
        pm_q2 = models.ProjectMember(project_id=proj_seo.id, user_id=u_multi.id)

        db.add_all([pm1, pm2, pm3, pm_q1, pm_q2])
        db.flush()

        # ----------------------------------------------------
        # 7. TASKS (Mixed Client Visible & Internal)
        # ----------------------------------------------------
        # Apex Website tasks
        t_web_1 = models.Task(
            agency_id=agency_apex.id,
            project_id=proj_website.id,
            title="Design Home Page Mockups",
            description="Create visual layouts for main desktop & mobile viewpoints.",
            status="completed",
            priority="high",
            assignee_id=u_apex_member.id,
            is_client_visible=True,
            due_date=datetime.datetime.utcnow() - datetime.timedelta(days=1)
        )
        
        t_web_2 = models.Task(
            agency_id=agency_apex.id,
            project_id=proj_website.id,
            title="Develop Backend API integration",
            description="Write API adapters to fetch content from the CRM endpoints.",
            status="in_progress",
            priority="medium",
            assignee_id=u_apex_member.id,
            is_client_visible=False, # INTERNAL ONLY
            due_date=datetime.datetime.utcnow() + datetime.timedelta(days=5)
        )
        
        t_web_3 = models.Task(
            agency_id=agency_apex.id,
            project_id=proj_website.id,
            title="Draft Frontend UI Architecture",
            description="Setup Vite configurations, CSS modules, and custom styling system.",
            status="in_review",
            priority="urgent",
            assignee_id=u_apex_admin.id,
            is_client_visible=True,
            due_date=datetime.datetime.utcnow() + datetime.timedelta(days=2)
        )
        
        t_web_4 = models.Task(
            agency_id=agency_apex.id,
            project_id=proj_website.id,
            title="Internal Code Quality Audit",
            description="Review bundle sizes and verify TypeScript compiler settings.",
            status="todo",
            priority="low",
            assignee_id=u_apex_member.id,
            is_client_visible=False, # INTERNAL ONLY
            due_date=datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )

        # Quantum SEO tasks
        t_seo_1 = models.Task(
            agency_id=agency_quantum.id,
            project_id=proj_seo.id,
            title="Initial Keyword Audit",
            description="Research 50 low-hanging-fruit search keywords.",
            status="completed",
            priority="medium",
            assignee_id=u_multi.id, # Morgan is assigned in Quantum
            is_client_visible=True,
            due_date=datetime.datetime.utcnow() - datetime.timedelta(days=3)
        )

        t_seo_2 = models.Task(
            agency_id=agency_quantum.id,
            project_id=proj_seo.id,
            title="Quantum Internal Pitch Prep",
            description="Build slides outlining secret SEO strategies for Quantum core team.",
            status="todo",
            priority="high",
            assignee_id=u_quantum_admin.id,
            is_client_visible=False, # INTERNAL ONLY
            due_date=datetime.datetime.utcnow() + datetime.timedelta(days=4)
        )

        db.add_all([t_web_1, t_web_2, t_web_3, t_web_4, t_seo_1, t_seo_2])
        db.flush()

        # ----------------------------------------------------
        # 8. COMMENTS
        # ----------------------------------------------------
        # Web Task 1 (Design Mockup - Client Visible) Comments
        c1 = models.Comment(
            agency_id=agency_apex.id,
            task_id=t_web_1.id,
            user_id=u_apex_member.id,
            content="Initial wireframe sketches are uploaded. Ready for Alpha Corp feedback.",
            is_client_visible=True
        )
        c2 = models.Comment(
            agency_id=agency_apex.id,
            task_id=t_web_1.id,
            user_id=u_apex_client.id,
            content="These look clean! We love the header layout. Can we make the hero text slightly bolder?",
            is_client_visible=True
        )
        c3 = models.Comment(
            agency_id=agency_apex.id,
            task_id=t_web_1.id,
            user_id=u_apex_member.id,
            content="[Internal Note] Client requested heavier font. I'll swap it to Outfit ExtraBold on the local theme file.",
            is_client_visible=False # INTERNAL ONLY
        )

        db.add_all([c1, c2, c3])
        db.flush()

        # ----------------------------------------------------
        # 9. TIME ENTRIES
        # ----------------------------------------------------
        te1 = models.TimeEntry(
            agency_id=agency_apex.id,
            task_id=t_web_1.id,
            user_id=u_apex_member.id,
            duration_minutes=240, # 4 hours
            note="Iterating on Figma desktop wireframes",
            date=datetime.date.today() - datetime.timedelta(days=2)
        )
        te2 = models.TimeEntry(
            agency_id=agency_apex.id,
            task_id=t_web_2.id,
            user_id=u_apex_member.id,
            duration_minutes=360, # 6 hours (Internal Task)
            note="Configuring SQL integrations and schemas",
            date=datetime.date.today() - datetime.timedelta(days=1)
        )
        te3 = models.TimeEntry(
            agency_id=agency_apex.id,
            task_id=t_web_3.id,
            user_id=u_apex_admin.id,
            duration_minutes=180, # 3 hours
            note="Discussing layout patterns and theme configuration",
            date=datetime.date.today()
        )
        
        # Quantum SEO task time
        te_q1 = models.TimeEntry(
            agency_id=agency_quantum.id,
            task_id=t_seo_1.id,
            user_id=u_multi.id,
            duration_minutes=300, # 5 hours
            note="Running tools to scrape keyword search volumes",
            date=datetime.date.today() - datetime.timedelta(days=2)
        )

        db.add_all([te1, te2, te3, te_q1])
        db.flush()

        # ----------------------------------------------------
        # 10. UPLOADED FILES
        # ----------------------------------------------------
        f1 = models.UploadedFile(
            agency_id=agency_apex.id,
            task_id=t_web_1.id,
            user_id=u_apex_member.id,
            filename="home_mockup_v1.png",
            file_path="mock_home_mockup_v1.png",
            mime_type="image/png",
            file_size=1048576, # 1 MB
            is_client_visible=True,
            approval_status="approved"
        )
        
        f2 = models.UploadedFile(
            agency_id=agency_apex.id,
            task_id=t_web_1.id,
            user_id=u_apex_member.id,
            filename="home_mockup_v2_ Outfit_bold.png",
            file_path="mock_home_mockup_v2.png",
            mime_type="image/png",
            file_size=1052300,
            is_client_visible=True,
            approval_status="pending"
        )
        
        f3 = models.UploadedFile(
            agency_id=agency_apex.id,
            task_id=t_web_2.id,
            user_id=u_apex_member.id,
            filename="db_credentials_audit.json",
            file_path="mock_db_audit.json",
            mime_type="application/json",
            file_size=512,
            is_client_visible=False, # INTERNAL ONLY
            approval_status="pending"
        )

        db.add_all([f1, f2, f3])
        db.commit()
        
        print("Database seeded successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {str(e)}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
