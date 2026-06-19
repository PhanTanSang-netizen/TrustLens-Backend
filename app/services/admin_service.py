from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.metadata_provider import MetadataProvider
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
