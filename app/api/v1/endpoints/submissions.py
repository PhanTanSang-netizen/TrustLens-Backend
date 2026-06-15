from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.submission_schema import SubmissionUploadResponse
from app.services.file_storage_service import validate_and_store_upload_file
from app.services.submission_service import (
    create_submission_with_file_and_job,
    get_assignment_by_id,
)


router = APIRouter()


@router.post(
    "/upload",
    response_model=SubmissionUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_submission_file(
    assignment_id: UUID = Form(...),
    owner_label: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    assignment = get_assignment_by_id(
        db=db,
        assignment_id=assignment_id,
    )

    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "ASSIGNMENT_NOT_FOUND",
                "message": "Không tìm thấy bài nộp cần thẩm định.",
                "details": {
                    "assignment_id": str(assignment_id),
                },
            },
        )

    if assignment.status != "OPEN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "ASSIGNMENT_NOT_OPEN",
                "message": "Assignment hiện không mở để upload.",
                "details": {
                    "assignment_id": str(assignment_id),
                    "status": assignment.status,
                },
            },
        )

    stored_file = await validate_and_store_upload_file(file)

    try:
        submission, db_file, job = create_submission_with_file_and_job(
            db=db,
            assignment_id=assignment_id,
            owner_label=owner_label,
            stored_file=stored_file,
            uploaded_by=current_user.id,
        )
    except Exception:
        db.rollback()
        raise

    return {
        "message": "Upload file thành công và đã lưu PostgreSQL.",
        "submission": submission,
        "file": db_file,
        "job": job,
    }