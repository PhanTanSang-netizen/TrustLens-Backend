from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User


def _coerce_uuid(value: UUID | str | None) -> UUID | None:
    if value is None or isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError:
        return None


def record_audit_log(
    db: Session,
    action: str,
    user_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    message: str | None = None,
    details: dict | None = None,
    actor_id: UUID | None = None,
    object_type: str | None = None,
    object_id: UUID | str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    resolved_actor_id = actor_id if actor_id is not None else user_id
    resolved_object_type = object_type if object_type is not None else resource_type
    resolved_object_id = _coerce_uuid(object_id if object_id is not None else resource_id)
    resolved_details = details.copy() if details is not None else {}

    if message:
        resolved_details.setdefault("message", message)

    audit_log = AuditLog(
        actor_id=resolved_actor_id,
        action=action,
        object_type=resolved_object_type,
        object_id=resolved_object_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details_json=resolved_details or None,
    )
    db.add(audit_log)
    db.flush()
    return audit_log


def get_audit_logs(db: Session, limit: int = 100) -> list[dict]:
    rows = db.execute(
        select(AuditLog, User)
        .outerjoin(User, AuditLog.actor_id == User.id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": audit_log.id,
            "action": audit_log.action,
            "user": user.email if user is not None else "system",
            "time": audit_log.created_at,
            "type": audit_log.object_type or "system",
            "message": (audit_log.details_json or {}).get("message"),
            "details": audit_log.details_json,
        }
        for audit_log, user in rows
    ]
