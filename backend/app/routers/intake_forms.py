import json
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db, current_user_id
from .. import auth, models, schemas
from ..services.event_bus import emit_notification, serialize_answers

router = APIRouter(prefix="/intake-forms", tags=["Client Intake Forms"])


def generate_share_token() -> str:
    return str(uuid.uuid4())


def serialize_form(form: models.ClientIntakeForm) -> dict:
    return {
        "id": form.id,
        "agency_id": form.agency_id,
        "title": form.title,
        "fields_schema": json.loads(form.fields_schema),
        "share_token": form.share_token,
        "is_active": form.is_active,
        "created_by": form.created_by,
        "updated_by": form.updated_by,
        "created_at": form.created_at,
        "updated_at": form.updated_at,
    }


@router.get("", response_model=List[schemas.ClientIntakeFormOut])
def list_intake_forms(
    membership: models.AgencyMembership = Depends(auth.require_roles(["agency_admin"])),
    db: Session = Depends(get_db),
):
    forms = (
        db.query(models.ClientIntakeForm)
        .filter(models.ClientIntakeForm.agency_id == membership.agency_id)
        .order_by(models.ClientIntakeForm.created_at.desc())
        .all()
    )
    return [serialize_form(form) for form in forms]


@router.post("", response_model=schemas.ClientIntakeFormOut, status_code=status.HTTP_201_CREATED)
def create_intake_form(
    payload: schemas.ClientIntakeFormCreate,
    membership: models.AgencyMembership = Depends(auth.require_roles(["agency_admin"])),
    db: Session = Depends(get_db),
):
    form = models.ClientIntakeForm(
        agency_id=membership.agency_id,
        title=payload.title,
        fields_schema=json.dumps(payload.fields_schema, ensure_ascii=False),
        share_token=generate_share_token(),
        is_active=payload.is_active,
    )
    db.add(form)
    db.commit()
    db.refresh(form)
    return serialize_form(form)


@router.post("/public/{share_token}", response_model=schemas.ClientIntakeSubmissionOut, status_code=status.HTTP_201_CREATED)
def submit_intake_form(
    share_token: str,
    payload: schemas.ClientIntakeSubmissionCreate,
    db: Session = Depends(get_db),
):
    form = (
        db.query(models.ClientIntakeForm)
        .filter(models.ClientIntakeForm.share_token == share_token)
        .first()
    )
    if not form or not form.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intake form not found.")

    client = models.Client(
        agency_id=form.agency_id,
        name=payload.client_name,
    )
    db.add(client)
    db.flush()

    project = models.Project(
        agency_id=form.agency_id,
        client_id=client.id,
        name=payload.project_name,
        description=payload.project_description,
    )
    db.add(project)
    db.flush()

    submission = models.ClientIntakeSubmission(
        agency_id=form.agency_id,
        form_id=form.id,
        client_id=client.id,
        project_id=project.id,
        client_name=payload.client_name,
        project_name=payload.project_name,
        answers_json=serialize_answers(payload.answers),
    )
    db.add(submission)
    emit_notification(
        db,
        agency_id=form.agency_id,
        event_type="intake_submission_created",
        title="New client intake submission",
        message=f"{payload.client_name} submitted a new intake for {payload.project_name}.",
        entity_type="intake_submission",
        entity_id=submission.id,
        client_visible=False,
    )
    db.commit()
    db.refresh(submission)
    return submission