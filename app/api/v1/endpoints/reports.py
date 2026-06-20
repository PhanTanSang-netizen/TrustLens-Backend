from uuid import UUID
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import require_permissions
from app.core.permissions import JOB_ANALYZE, REPORT_EXPORT, REPORT_VIEW_OWN_SCOPE
from app.db.session import get_db
from app.schemas.report_schema import ReportHistoryItem, SubmissionReportResponse
from app.services.export_service import (
    export_submission_report_to_docx,
    export_submission_report_to_pdf,
    export_submission_report_to_xlsx,
)
from app.services.report_service import (
    get_report_by_submission,
    get_report_history,
    resolve_submission_id_for_report_route,
)

router = APIRouter()


def _build_file_response(export_record) -> FileResponse:
    stored_path = (
        getattr(export_record, "stored_path", None)
        or getattr(export_record, "storage_path", None)
    )

    if not stored_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "EXPORT_FILE_PATH_MISSING",
                "message": "Export đã tạo nhưng thiếu đường dẫn file.",
                "details": {"export_id": str(getattr(export_record, "id", ""))},
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
                    "export_id": str(getattr(export_record, "id", "")),
                    "stored_path": str(stored_path),
                },
            },
        )

    file_name = (
        getattr(export_record, "file_name", None)
        or file_path.name
    )
    mime_type = getattr(export_record, "mime_type", None)

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

    return FileResponse(
        path=str(file_path),
        media_type=mime_type,
        filename=file_name,
    )


@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionReportResponse,
)
def get_submission_report_endpoint(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(REPORT_VIEW_OWN_SCOPE)),
):
    return get_report_by_submission(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
    )


@router.post(
    "/submissions/{submission_id}/generate",
    response_model=SubmissionReportResponse,
)
def generate_submission_report_endpoint(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(JOB_ANALYZE)),
):
    return get_report_by_submission(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
    )


@router.get(
    "/submissions/{submission_id}/export/docx",
)
def export_submission_report_docx_endpoint(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(REPORT_EXPORT)),
):
    resolved_submission_id = resolve_submission_id_for_report_route(
        db=db,
        submission_or_report_id=submission_id,
        current_user=current_user,
    )
    get_report_by_submission(
        db=db,
        submission_id=resolved_submission_id,
        current_user=current_user,
    )

    exported_file = export_submission_report_to_docx(
        db=db,
        submission_id=resolved_submission_id,
        current_user=current_user,
    )

    return _build_file_response(exported_file)


@router.get(
    "/submissions/{submission_id}/export/pdf",
)
def export_submission_report_pdf_endpoint(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(REPORT_EXPORT)),
):
    resolved_submission_id = resolve_submission_id_for_report_route(
        db=db,
        submission_or_report_id=submission_id,
        current_user=current_user,
    )
    get_report_by_submission(
        db=db,
        submission_id=resolved_submission_id,
        current_user=current_user,
    )

    exported_file = export_submission_report_to_pdf(
        db=db,
        submission_id=resolved_submission_id,
        current_user=current_user,
    )

    return _build_file_response(exported_file)


@router.get(
    "/submissions/{submission_id}/export/xlsx",
)
def export_submission_report_xlsx_endpoint(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(REPORT_EXPORT)),
):
    resolved_submission_id = resolve_submission_id_for_report_route(
        db=db,
        submission_or_report_id=submission_id,
        current_user=current_user,
    )
    get_report_by_submission(
        db=db,
        submission_id=resolved_submission_id,
        current_user=current_user,
    )

    exported_file = export_submission_report_to_xlsx(
        db=db,
        submission_id=resolved_submission_id,
        current_user=current_user,
    )

    return _build_file_response(exported_file)

@router.get(
    "/{report_id}/history",
    response_model=list[ReportHistoryItem],
)
def get_report_history_endpoint(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(REPORT_VIEW_OWN_SCOPE)),
):
    return get_report_history(
        db=db,
        report_id=report_id,
        current_user=current_user,
    )

