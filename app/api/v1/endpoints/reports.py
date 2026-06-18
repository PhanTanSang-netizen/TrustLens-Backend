from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.report_schema import SubmissionReportResponse
from app.services.report_service import get_submission_report

router = APIRouter()


@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionReportResponse,
)
def get_submission_report_endpoint(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return get_submission_report(
        db=db,
        submission_id=submission_id,
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
    return get_submission_report(
        db=db,
        submission_id=submission_id,
    )