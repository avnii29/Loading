import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import NotificationType
from app.models.ops import Notification


def create_notification(
    db: Session,
    *,
    user_id: uuid.UUID,
    ntype: NotificationType,
    title: str,
    body: str,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
) -> Notification:
    note = Notification(
        user_id=user_id,
        type=ntype,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db.add(note)
    return note


def list_for_user(db: Session, user_id: uuid.UUID, unread_only: bool = False) -> list[Notification]:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.order_by(Notification.created_at.desc())
    return list(db.scalars(stmt))


def mark_read(db: Session, notification: Notification) -> Notification:
    notification.is_read = True
    db.add(notification)
    return notification
