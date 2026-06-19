from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.report_schema import ReportExportCreate
from app.services.access_control_service import get_accessible_report_or_404
from app.services.export_service import create_report_export
from app.services.report_service import get_report, get_report_history


router = APIRouter()


@router.get("/{report_id}")
def read_report(report_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return get_report(db=db, report_id=report_id, current_user=current_user)


@router.get("/{report_id}/history")
def read_report_history(report_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return get_report_history(db=db, report_id=report_id, current_user=current_user)


@router.post("/{report_id}/exports")
def export_report(report_id: UUID, payload: ReportExportCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    report = get_accessible_report_or_404(db=db, report_id=report_id, user=current_user)
    report_export = create_report_export(db=db, report=report, export_format=payload.format, include_raw_citation=payload.include_raw_citation, created_by=current_user.id)
    return {"export_id": report_export.id, "format": report_export.format, "status": report_export.status, "download_url": f"/api/v1/report-exports/{report_export.id}/download", "created_at": report_export.created_at}
