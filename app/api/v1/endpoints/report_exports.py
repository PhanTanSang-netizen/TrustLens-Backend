from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.services.access_control_service import get_accessible_export_or_404


router = APIRouter()


@router.get("/{export_id}/download")
def download_report_export(export_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    report_export = get_accessible_export_or_404(db=db, export_id=export_id, user=current_user)
    return FileResponse(report_export.storage_path, media_type="application/pdf", filename=f"TrustLens_Report_{report_export.report_id}.pdf")
