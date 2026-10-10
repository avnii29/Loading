import uuid

from sqlalchemy.orm import Session

from app.models.ops import AuditLog


def write_audit(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    actor_id: uuid.UUID | None = None,
    extra: dict | None = None,
) -> AuditLog:
    safe_extra = None
    if extra:
        blocked = {"password", "token", "secret", "verification_code", "code"}
        safe_extra = {k: v for k, v in extra.items() if k not in blocked}
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        extra=safe_extra,
    )
    db.add(entry)
    return entry
