from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User


def record_audit_log(
    db: Session,
    action: str,
    user_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    message: str | None = None,
    details: dict | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        message=message,
        details=details,
    )
    db.add(audit_log)
    db.flush()
    return audit_log


def get_audit_logs(db: Session, limit: int = 100) -> list[dict]:
    rows = db.execute(
        select(AuditLog, User)
        .outerjoin(User, AuditLog.user_id == User.id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": audit_log.id,
            "action": audit_log.action,
            "user": user.email if user is not None else "system",
            "time": audit_log.created_at,
            "type": audit_log.resource_type or "system",
            "message": audit_log.message,
            "details": audit_log.details,
        }
        for audit_log, user in rows
    ]
