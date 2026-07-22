import json
from typing import Optional

from sqlalchemy.orm import Session

from .. import models


def emit_notification(
    db: Session,
    *,
    agency_id: str,
    event_type: str,
    title: str,
    message: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    client_visible: bool = True,
    actor_user_id: Optional[str] = None,
) -> None:
    recipients = db.query(models.AgencyMembership).filter(models.AgencyMembership.agency_id == agency_id)
    if not client_visible:
        recipients = recipients.filter(models.AgencyMembership.role != "client_user")

    for membership in recipients.all():
        if actor_user_id and membership.user_id == actor_user_id:
            continue

        db.add(
            models.Notification(
                agency_id=agency_id,
                user_id=membership.user_id,
                event_type=event_type,
                title=title,
                message=message,
                entity_type=entity_type,
                entity_id=entity_id,
                is_read=False,
            )
        )


def serialize_answers(answers: dict) -> str:
    return json.dumps(answers, ensure_ascii=False, sort_keys=True)