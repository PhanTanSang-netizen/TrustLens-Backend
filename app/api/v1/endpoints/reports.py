from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.report_schema import SubmissionReportResponse
from app.services.export_service import (
    export_submission_report_to_docx,
    export_submission_report_to_pdf,
    export_submission_report_to_xlsx,
)
from app.services.report_service import get_report_by_submission

router = APIRouter()


def _build_file_response(exported_file) -> Response:
    return Response(
        content=exported_file.content,
        media_type=exported_file.media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{exported_file.filename}"'
            )
        },
    )


@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionReportResponse,
)
def get_submission_report_endpoint(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
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
    current_user=Depends(get_current_user),
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
    current_user=Depends(get_current_user),
):
    exported_file = export_submission_report_to_docx(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
    )

    return _build_file_response(exported_file)


@router.get(
    "/submissions/{submission_id}/export/pdf",
)
def export_submission_report_pdf_endpoint(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    exported_file = export_submission_report_to_pdf(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
    )

    return _build_file_response(exported_file)


@router.get(
    "/submissions/{submission_id}/export/xlsx",
)
def export_submission_report_xlsx_endpoint(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    exported_file = export_submission_report_to_xlsx(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
    )

    return _build_file_response(exported_file)
