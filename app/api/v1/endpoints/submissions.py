from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.extracted_document_schema import AnalyzeSubmissionResponse
from app.schemas.submission_schema import SubmissionUploadResponse
from app.services.extraction_service import analyze_submission_text
from app.services.file_storage_service import validate_and_store_upload_file
from app.services.submission_service import (
    create_submission_with_file_and_job,
    get_assignment_by_id,
)

from app.schemas.reference_section_schema import DetectReferenceSectionResponse
from app.services.reference_section_service import detect_and_save_reference_section
from app.schemas.citation_schema import ParseCitationsResponse
from app.services.citation_service import parse_and_save_citations

from app.schemas.metadata_record_schema import VerifyMetadataResponse
from app.services.metadata_verification_service import verify_submission_metadata

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


@router.post(
    "/{submission_id}/analyze",
    response_model=AnalyzeSubmissionResponse,
)
def analyze_submission_endpoint(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job, extracted_document = analyze_submission_text(
        db=db,
        submission_id=submission_id,
    )

    return {
        "message": "Trích xuất text từ tài liệu thành công.",
        "job": job,
        "extracted_document": extracted_document,
    }

@router.post(
    "/{submission_id}/detect-references",
    response_model=DetectReferenceSectionResponse,
)
def detect_reference_section_endpoint(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job, reference_section = detect_and_save_reference_section(
        db=db,
        submission_id=submission_id,
    )

    return {
        "message": "Nhận diện phần tài liệu tham khảo thành công.",
        "job": job,
        "reference_section": reference_section,
    }

@router.post(
    "/{submission_id}/parse-citations",
    response_model=ParseCitationsResponse,
)
def parse_citations_endpoint(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job, citations = parse_and_save_citations(
        db=db,
        submission_id=submission_id,
    )

    return {
        "message": "Tách citation thành công.",
        "total": len(citations),
        "job": job,
        "citations": citations,
    }

@router.post(
    "/{submission_id}/verify-metadata",
    response_model=VerifyMetadataResponse,
)
def verify_metadata_endpoint(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job, records = verify_submission_metadata(
        db=db,
        submission_id=submission_id,
    )

    verified = len([
        record
        for record in records
        if record.verification_status == "URL_OK"
    ])

    broken = len([
        record
        for record in records
        if record.verification_status == "URL_BROKEN"
    ])

    forbidden = len([
        record
        for record in records
        if record.verification_status == "URL_FORBIDDEN"
    ])

    unreachable = len([
        record
        for record in records
        if record.verification_status == "URL_UNREACHABLE"
    ])

    not_provided = len([
        record
        for record in records
        if record.verification_status == "URL_NOT_PROVIDED"
    ])

    return {
        "message": "Kiểm chứng metadata URL thành công.",
        "total": len(records),
        "verified": verified,
        "broken": broken,
        "forbidden": forbidden,
        "unreachable": unreachable,
        "not_provided": not_provided,
        "job": job,
        "records": records,
    }