from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.ops import Notification
from app.models.user import User
from app.schemas.common import NotificationOut
from app.services.notification import list_for_user, mark_read

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = list_for_user(db, user.id)
    return [
        NotificationOut(
            id=str(row.id),
            type=row.type.value,
            title=row.title,
            body=row.body,
            entity_type=row.entity_type,
            entity_id=str(row.entity_id) if row.entity_id else None,
            is_read=row.is_read,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/{notification_id}/read", response_model=NotificationOut)
def read_one(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(Notification, notification_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notification not found.")
    mark_read(db, row)
    db.commit()
    return NotificationOut(
        id=str(row.id),
        type=row.type.value,
        title=row.title,
        body=row.body,
        entity_type=row.entity_type,
        entity_id=str(row.entity_id) if row.entity_id else None,
        is_read=row.is_read,
        created_at=row.created_at,
    )
