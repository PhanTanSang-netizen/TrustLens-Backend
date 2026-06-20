from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.services.access_control_service import get_accessible_export_or_404


router = APIRouter()


@router.get("/{export_id}/download")
def download_report_export(
    export_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    report_export = get_accessible_export_or_404(
        db=db,
        export_id=export_id,
        current_user=current_user,
    )

    stored_path = (
        getattr(report_export, "stored_path", None)
        or getattr(report_export, "storage_path", None)
    )

    if not stored_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "EXPORT_FILE_PATH_NOT_FOUND",
                "message": "Không tìm thấy đường dẫn file export.",
                "details": {
                    "export_id": str(export_id),
                },
            },
        )

    file_path = Path(stored_path)

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "EXPORT_FILE_NOT_FOUND",
                "message": "File export không tồn tại trên hệ thống.",
                "details": {
                    "export_id": str(export_id),
                    "stored_path": str(stored_path),
                },
            },
        )

    mime_type = getattr(report_export, "mime_type", None)

    if not mime_type:
        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            mime_type = "application/pdf"
        elif suffix == ".docx":
            mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif suffix == ".xlsx":
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            mime_type = "application/octet-stream"

    file_name = getattr(report_export, "file_name", None)

    if not file_name:
        file_name = f"TrustLens_Report_{report_export.report_id}{file_path.suffix}"

    return FileResponse(
        path=str(file_path),
        media_type=mime_type,
        filename=file_name,
    )