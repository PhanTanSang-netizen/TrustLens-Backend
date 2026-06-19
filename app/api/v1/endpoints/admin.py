from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.schemas.metadata_provider_schema import MetadataProviderRead, MetadataProviderUpdate
from app.services.admin_service import list_audit_logs, list_metadata_providers, update_metadata_provider


router = APIRouter()


@router.get("/audit-logs")
def read_audit_logs(db: Session = Depends(get_db), current_user=Depends(require_admin)):
    return list_audit_logs(db=db)


@router.get("/metadata-providers", response_model=list[MetadataProviderRead])
def read_metadata_providers(db: Session = Depends(get_db), current_user=Depends(require_admin)):
    return list_metadata_providers(db=db)


@router.put("/metadata-providers/{provider_id}", response_model=MetadataProviderRead)
def update_provider(provider_id: UUID, payload: MetadataProviderUpdate, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    return update_metadata_provider(db=db, provider_id=provider_id, payload=payload, updated_by=current_user.id)
