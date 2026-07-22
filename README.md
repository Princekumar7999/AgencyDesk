# AgencyDesk

Multi-tenant agency and client portal built with FastAPI and Next.js.

## Quick Start

Backend:

```bash
cd backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

- Frontend: http://localhost:3000
- Backend docs: http://localhost:8000/docs

## Verify The Rules

Run the backend tests that prove tenant isolation, client visibility, invite safety, audit fields, and member removal:

```bash
cd backend
python3 -m pytest -q tests/test_api.py
```

## What To Show In A Demo Video

1. Log in as Alice or Quincy and create a client company first.
2. Create a project using that client company.
3. Show the client portal account only seeing client-visible items.
4. Switch agencies for the multi-agency user and show the role changes.
5. Open the intake form flow and show the public submission creating a client and project.
