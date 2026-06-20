from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_permissions
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
