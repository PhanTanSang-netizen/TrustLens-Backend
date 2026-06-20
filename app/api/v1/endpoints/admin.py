from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.ai.embeddings.factory import create_embedding_provider
from app.ai.relevance.relevance_service import ReferenceInput, RelevanceService
from app.api.deps import require_permissions
from app.core.config import settings
from app.core.permissions import (
    ADMIN_AUDIT_LOG,
    ADMIN_METADATA_PROVIDER,
    ADMIN_USER_MANAGE,
)
from app.db.session import get_db
from app.schemas.admin_schema import AdminUserCreate, AdminUserRead, AdminUserUpdate
from app.schemas.metadata_provider_schema import MetadataProviderRead, MetadataProviderUpdate
from app.services.admin_service import (
    create_managed_user,
    deactivate_managed_user,
    list_audit_logs,
    list_metadata_providers,
    list_users,
    update_managed_user,
    update_metadata_provider,
)


router = APIRouter()


@router.get("/system/ai-health")
async def ai_health(
    current_user=Depends(require_permissions(ADMIN_METADATA_PROVIDER)),
):
    del current_user
    primary = create_embedding_provider(settings.RELEVANCE_PROVIDER)
    fallback = create_embedding_provider(settings.RELEVANCE_FALLBACK_PROVIDER)
    probe = "TrustLens technical health probe for embedding availability."
    primary_result = await primary.embed_query(probe)
    fallback_result = await fallback.embed_query(probe)
    return {
        "primary_provider": settings.RELEVANCE_PROVIDER,
        "primary_status": "available" if primary_result.status == "SUCCESS" else "unavailable",
        "primary_error_code": primary_result.error_code,
        "fallback_provider": settings.RELEVANCE_FALLBACK_PROVIDER,
        "fallback_status": "available" if fallback_result.status == "SUCCESS" else "unavailable",
        "fallback_error_code": fallback_result.error_code,
        "model_id": primary_result.model_id,
        "prompt_version": settings.RELEVANCE_PROMPT_VERSION,
    }


@router.post("/relevance/diagnose")
async def diagnose_relevance(
    payload: dict,
    current_user=Depends(require_permissions(ADMIN_METADATA_PROVIDER)),
):
    del current_user
    service = RelevanceService()
    result = await service.score_reference(
        report_text=str(payload.get("report_text") or ""),
        report_context={"body_text": str(payload.get("report_text") or "")},
        reference=ReferenceInput(
            title=payload.get("reference_title"),
            abstract=payload.get("reference_abstract"),
            keywords=payload.get("reference_keywords"),
            venue=payload.get("reference_venue"),
            raw_citation=payload.get("raw_citation"),
        ),
    )
    return {
        "score": result.score,
        "max_score": result.max_score,
        "confidence": result.confidence,
        "reason": result.reason,
        "evidence": result.evidence,
    }


@router.get("/audit-logs")
def read_audit_logs(
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(ADMIN_AUDIT_LOG)),
):
    return list_audit_logs(db=db)


@router.get("/metadata-providers", response_model=list[MetadataProviderRead])
def read_metadata_providers(
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(ADMIN_METADATA_PROVIDER)),
):
    return list_metadata_providers(db=db)


@router.put("/metadata-providers/{provider_id}", response_model=MetadataProviderRead)
def update_provider(
    provider_id: UUID,
    payload: MetadataProviderUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(ADMIN_METADATA_PROVIDER)),
):
    return update_metadata_provider(db=db, provider_id=provider_id, payload=payload, updated_by=current_user.id)


@router.get("/users", response_model=list[AdminUserRead])
def read_users(
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(ADMIN_USER_MANAGE)),
):
    return list_users(db=db)


@router.post("/users", response_model=AdminUserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(ADMIN_USER_MANAGE)),
):
    return create_managed_user(db=db, payload=payload, created_by=current_user.id)


@router.put("/users/{user_id}", response_model=AdminUserRead)
def update_user(
    user_id: UUID,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(ADMIN_USER_MANAGE)),
):
    return update_managed_user(db=db, user_id=user_id, payload=payload, updated_by=current_user.id)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(ADMIN_USER_MANAGE)),
):
    deactivate_managed_user(db=db, user_id=user_id, deleted_by=current_user.id)
    return None
