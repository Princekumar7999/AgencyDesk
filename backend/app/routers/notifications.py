from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import auth, models, schemas

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[schemas.NotificationOut])
def list_notifications(
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Notification)
        .filter(
            models.Notification.agency_id == membership.agency_id,
            models.Notification.user_id == membership.user_id,
        )
        .order_by(models.Notification.created_at.desc())
        .all()
    )


@router.post("/{notification_id}/read", response_model=schemas.NotificationOut)
def mark_notification_read(
    notification_id: str,
    membership: models.AgencyMembership = Depends(auth.get_current_membership),
    db: Session = Depends(get_db),
):
    notification = (
        db.query(models.Notification)
        .filter(
            models.Notification.id == notification_id,
            models.Notification.agency_id == membership.agency_id,
            models.Notification.user_id == membership.user_id,
        )
        .first()
    )
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")

    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification