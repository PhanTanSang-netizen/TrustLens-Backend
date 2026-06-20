from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.metadata_provider import MetadataProvider
from app.models.user import User
from app.schemas.admin_schema import serialize_admin_user
from app.services.audit_service import get_audit_logs, record_audit_log


DEFAULT_PROVIDERS = [
    {"name": "Crossref API", "code": "crossref", "base_url": "https://api.crossref.org", "enabled": True, "priority": 1, "status": "healthy"},
    {"name": "OpenAlex API", "code": "openalex", "base_url": "https://api.openalex.org", "enabled": True, "priority": 2, "status": "healthy"},
    {"name": "Semantic Scholar API", "code": "semantic_scholar", "base_url": "https://api.semanticscholar.org", "enabled": False, "priority": 3, "status": "disabled"},
]


def ensure_default_metadata_providers(db: Session) -> None:
    existing_codes = {provider.code for provider in db.execute(select(MetadataProvider)).scalars().all()}
    for provider_data in DEFAULT_PROVIDERS:
        if provider_data["code"] not in existing_codes:
            db.add(MetadataProvider(**provider_data))
    db.commit()


def list_metadata_providers(db: Session) -> list[MetadataProvider]:
    ensure_default_metadata_providers(db)
    return list(db.execute(select(MetadataProvider).order_by(MetadataProvider.priority.asc())).scalars().all())


def update_metadata_provider(db: Session, provider_id: UUID, payload, updated_by: UUID) -> MetadataProvider:
    ensure_default_metadata_providers(db)
    provider = db.execute(select(MetadataProvider).where(MetadataProvider.id == provider_id)).scalar_one_or_none()
    if provider is None:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error_code": "METADATA_PROVIDER_NOT_FOUND", "message": "Metadata provider not found.", "details": {"provider_id": str(provider_id)}})
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(provider, field, value)
    if "enabled" in update_data:
        provider.status = "healthy" if update_data["enabled"] else "disabled"
    record_audit_log(db=db, user_id=updated_by, action="UPDATE_METADATA_PROVIDER", resource_type="metadata_provider", resource_id=str(provider.id), message="Metadata provider updated.", details=update_data)
    db.commit()
    db.refresh(provider)
    return provider


def list_audit_logs(db: Session) -> list[dict]:
    return get_audit_logs(db=db, limit=100)


def _normalize_admin_role(role: str) -> str:
    normalized = str(role or "").strip().lower()
    if normalized not in {"admin", "lecturer", "student"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "ADMIN_INVALID_ROLE",
                "message": "Vai trò không hợp lệ.",
                "details": {"role": role},
            },
        )
    return normalized


def list_users(db: Session) -> list[dict]:
    users = db.execute(
        select(User).order_by(User.created_at.desc())
    ).scalars().all()
    return [serialize_admin_user(user) for user in users]


def create_managed_user(db: Session, payload, created_by: UUID) -> dict:
    existing_user = db.execute(
        select(User).where(User.email == str(payload.email).strip().lower())
    ).scalar_one_or_none()

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "ADMIN_USER_EMAIL_EXISTS",
                "message": "Email đã được sử dụng.",
                "details": {"email": str(payload.email)},
            },
        )

    temporary_password = payload.password or "123456"
    user = User(
        email=str(payload.email).strip().lower(),
        full_name=payload.full_name.strip(),
        role=_normalize_admin_role(payload.role),
        password_hash=get_password_hash(temporary_password),
        is_active=payload.status == "active",
    )
    db.add(user)
    db.flush()
    record_audit_log(
        db=db,
        user_id=created_by,
        action="CREATE_USER",
        resource_type="user",
        resource_id=str(user.id),
        message="Admin created user account.",
        details={"email": user.email, "role": user.role},
    )
    db.commit()
    db.refresh(user)
    return serialize_admin_user(user)


def update_managed_user(db: Session, user_id: UUID, payload, updated_by: UUID) -> dict:
    user = db.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "ADMIN_USER_NOT_FOUND",
                "message": "Không tìm thấy người dùng.",
                "details": {"user_id": str(user_id)},
            },
        )

    update_data = payload.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"] is not None:
        next_email = str(update_data["email"]).strip().lower()
        existing_user = db.execute(
            select(User).where(User.email == next_email, User.id != user_id)
        ).scalar_one_or_none()
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error_code": "ADMIN_USER_EMAIL_EXISTS",
                    "message": "Email đã được sử dụng.",
                    "details": {"email": next_email},
                },
            )
        user.email = next_email

    if "full_name" in update_data and update_data["full_name"] is not None:
        user.full_name = str(update_data["full_name"]).strip()

    if "role" in update_data and update_data["role"] is not None:
        user.role = _normalize_admin_role(update_data["role"])

    if "status" in update_data and update_data["status"] is not None:
        user.is_active = update_data["status"] == "active"

    record_audit_log(
        db=db,
        user_id=updated_by,
        action="UPDATE_USER",
        resource_type="user",
        resource_id=str(user.id),
        message="Admin updated user account.",
        details=update_data,
    )
    db.commit()
    db.refresh(user)
    return serialize_admin_user(user)


def deactivate_managed_user(db: Session, user_id: UUID, deleted_by: UUID) -> None:
    user = db.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "ADMIN_USER_NOT_FOUND",
                "message": "Không tìm thấy người dùng.",
                "details": {"user_id": str(user_id)},
            },
        )

    user.is_active = False
    record_audit_log(
        db=db,
        user_id=deleted_by,
        action="DEACTIVATE_USER",
        resource_type="user",
        resource_id=str(user.id),
        message="Admin deactivated user account.",
    )
    db.commit()
