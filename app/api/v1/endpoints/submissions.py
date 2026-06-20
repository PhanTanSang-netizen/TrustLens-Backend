from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import require_permissions
from app.core.enums.metadata_status import MetadataStatus, normalize_metadata_status
from app.core.permissions import JOB_ANALYZE, SUBMISSION_UPLOAD
from app.db.session import get_db
from app.schemas.citation_schema import ParseCitationsResponse
from app.schemas.job_schema import AnalyzeJobResponse
from app.schemas.metadata_record_schema import VerifyMetadataResponse
from app.schemas.reference_section_schema import DetectReferenceSectionResponse
from app.schemas.submission_schema import SubmissionUploadResponse
from app.services.access_control_service import (
    ensure_assignment_access_or_admin,
    ensure_submission_access_or_admin,
)
from app.services.analysis_pipeline_service import run_analysis_pipeline
from app.services.job_service import create_queued_job
from app.services.audit_service import record_audit_log
from app.services.citation_service import parse_and_save_citations
from app.services.file_storage_service import validate_and_store_upload_file
from app.services.job_service import run_submission_processing_pipeline
from app.services.metadata_verification_service import verify_submission_metadata
from app.services.reference_section_service import detect_and_save_reference_section
from app.services.submission_service import create_submission_with_file_and_job, get_assignment_by_id


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
    current_user=Depends(require_permissions(SUBMISSION_UPLOAD)),
):
    assignment = ensure_assignment_access_or_admin(
        db=db,
        assignment_id=assignment_id,
        current_user=current_user,
    )

    if assignment.status != "OPEN":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error_code": "ASSIGNMENT_NOT_OPEN", "message": "Assignment is not open for upload.", "details": {"assignment_id": str(assignment_id), "status": assignment.status}})
    stored_file = await validate_and_store_upload_file(file)
    try:
        submission, db_file, job = create_submission_with_file_and_job(db=db, assignment_id=assignment_id, owner_label=owner_label, stored_file=stored_file, uploaded_by=current_user.id)
        record_audit_log(db=db, user_id=current_user.id, action="UPLOAD_SUBMISSION", resource_type="submission", resource_id=str(submission.id), message="Submission file uploaded.", details={"assignment_id": str(assignment_id), "file_id": str(db_file.id)})
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(db_file)
    db.refresh(submission)
    db.refresh(job)

    return {
        "message": "Upload file successfully.",
        "id": submission.id,
        "submission_id": submission.id,
        "file_id": db_file.id,
        "job_id": job.id,
        "status": submission.status,
        "submission": submission,
        "file": db_file,
        "job": job,
    }


@router.post(
    "/{submission_id}/analyze",
    response_model=AnalyzeJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def analyze_submission_endpoint(
    submission_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(JOB_ANALYZE)),
):
    ensure_submission_access_or_admin(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
    )

    job = create_queued_job(
        db=db,
        submission_id=submission_id,
        created_by=getattr(current_user, "id", None),
    )
    background_tasks.add_task(run_analysis_pipeline, str(job.id))

    return {
        "job_id": job.id,
        "submission_id": job.submission_id,
        "status": job.status,
        "progress": job.progress,
        "created_at": job.created_at,
    }

@router.post(
    "/{submission_id}/detect-references",
    response_model=DetectReferenceSectionResponse,
)
def detect_reference_section_endpoint(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(JOB_ANALYZE)),
):
    ensure_submission_access_or_admin(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
    )
    
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
    current_user=Depends(require_permissions(JOB_ANALYZE)),
):
    ensure_submission_access_or_admin(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
    )
    
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
    current_user=Depends(require_permissions(JOB_ANALYZE)),
):
    ensure_submission_access_or_admin(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
    )

    job, records = verify_submission_metadata(
        db=db,
        submission_id=submission_id,
    )

    def count_by_status(statuses: list[MetadataStatus]) -> int:
        return len([
            record
            for record in records
            if normalize_metadata_status(record.verification_status) in statuses
        ])

    def count_by_status_and_provider(statuses: list[MetadataStatus], providers: set[str]) -> int:
        return len([
            record
            for record in records
            if normalize_metadata_status(record.verification_status) in statuses
            and record.provider in providers
        ])

    academic_verified = count_by_status([
        MetadataStatus.VERIFIED,
    ])

    academic_partial = count_by_status([
        MetadataStatus.PARTIAL_MATCH,
    ])

    academic_ambiguous = count_by_status([
        MetadataStatus.AMBIGUOUS,
    ])

    academic_not_found = count_by_status([
        MetadataStatus.NOT_FOUND,
    ])

    academic_lookup_attempted = len([
        record
        for record in records
        if record.provider in [
            "Crossref",
            "OpenAlex",
        ]
        or (
            isinstance(record.raw_response, dict)
            and isinstance(record.raw_response.get("academic_match_attempt"), dict)
        )
    ])

    doi_ok = count_by_status_and_provider([
        MetadataStatus.URL_ONLY,
    ], {"DOI_CHECK"})

    doi_unreachable = count_by_status_and_provider([
        MetadataStatus.PROVIDER_UNAVAILABLE,
    ], {"DOI_CHECK"})

    url_ok = count_by_status_and_provider([
        MetadataStatus.URL_ONLY,
    ], {"URL_CHECK"})

    url_weak_evidence = 0

    url_broken = count_by_status_and_provider([
        MetadataStatus.NOT_FOUND,
    ], {"URL_CHECK"})

    url_forbidden = 0

    url_unreachable = count_by_status_and_provider([
        MetadataStatus.PROVIDER_UNAVAILABLE,
    ], {"URL_CHECK"})

    basic_metadata_present = 0

    not_provided = count_by_status([
        MetadataStatus.NOT_FOUND,
    ])

    # Legacy field:
    # verified không còn tính URL_OK nữa.
    # Vì URL_OK chỉ chứng minh link sống, không chứng minh tài liệu học thuật khớp.
    verified = academic_verified

    return {
        "message": "Kiểm chứng metadata thành công.",
        "total": len(records),

        "verified": verified,

        "academic_verified": academic_verified,
        "academic_partial": academic_partial,
        "academic_ambiguous": academic_ambiguous,
        "academic_not_found": academic_not_found,
        "academic_lookup_attempted": academic_lookup_attempted,

        "doi_ok": doi_ok,
        "doi_unreachable": doi_unreachable,
        "url_ok": url_ok,
        "url_weak_evidence": url_weak_evidence,
        "url_broken": url_broken,
        "url_forbidden": url_forbidden,
        "url_unreachable": url_unreachable,

        "basic_metadata_present": basic_metadata_present,

        # Legacy-compatible summary
        "broken": url_broken,
        "forbidden": url_forbidden,
        "unreachable": url_unreachable + doi_unreachable,
        "not_provided": not_provided,

        "job": job,
        "records": records,
    }
