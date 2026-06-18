from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.processing_job import ProcessingJob
from app.models.submission import Submission
from app.services.citation_service import parse_and_save_citations
from app.services.extraction_service import analyze_submission_text
from app.services.metadata_verification_service import verify_submission_metadata
from app.services.reference_section_service import detect_and_save_reference_section


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_job_by_id(
    db: Session,
    job_id: UUID,
) -> ProcessingJob | None:
    return db.execute(
        select(ProcessingJob).where(ProcessingJob.id == job_id)
    ).scalar_one_or_none()


def get_submission_by_id(
    db: Session,
    submission_id: UUID,
) -> Submission | None:
    return db.execute(
        select(Submission).where(Submission.id == submission_id)
    ).scalar_one_or_none()


def get_latest_job_by_submission_id(
    db: Session,
    submission_id: UUID,
) -> ProcessingJob | None:
    return db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.submission_id == submission_id)
        .order_by(ProcessingJob.created_at.desc())
    ).scalars().first()


def create_processing_job(
    db: Session,
    submission_id: UUID,
    step: str = "queued",
) -> ProcessingJob:
    job = ProcessingJob(
        submission_id=submission_id,
        status="QUEUED",
        progress=0,
        step=step,
        error_code=None,
        started_at=None,
        finished_at=None,
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


def ensure_submission_exists(
    db: Session,
    submission_id: UUID,
) -> Submission:
    submission = get_submission_by_id(
        db=db,
        submission_id=submission_id,
    )

    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "SUBMISSION_NOT_FOUND",
                "message": "Không tìm thấy bài nộp.",
                "details": {
                    "submission_id": str(submission_id),
                },
            },
        )

    return submission


def mark_job_processing(
    db: Session,
    job: ProcessingJob,
    step: str,
    progress: int,
) -> ProcessingJob:
    job.status = "PROCESSING"
    job.step = step
    job.progress = progress
    job.error_code = None

    if job.started_at is None:
        job.started_at = utc_now()

    job.finished_at = None

    db.commit()
    db.refresh(job)

    return job


def mark_job_completed(
    db: Session,
    job: ProcessingJob,
    step: str = "pipeline_completed",
) -> ProcessingJob:
    job.status = "COMPLETED"
    job.step = step
    job.progress = 100
    job.error_code = None

    if job.started_at is None:
        job.started_at = utc_now()

    job.finished_at = utc_now()

    db.commit()
    db.refresh(job)

    return job


def mark_job_failed(
    db: Session,
    job: ProcessingJob,
    error_code: str,
    step: str = "pipeline_failed",
) -> ProcessingJob:
    job.status = "FAILED"
    job.step = step
    job.progress = 100
    job.error_code = error_code

    if job.started_at is None:
        job.started_at = utc_now()

    job.finished_at = utc_now()

    db.commit()
    db.refresh(job)

    return job


def run_submission_processing_pipeline(
    db: Session,
    submission_id: UUID,
) -> dict[str, Any]:
    submission = ensure_submission_exists(
        db=db,
        submission_id=submission_id,
    )

    job = create_processing_job(
        db=db,
        submission_id=submission_id,
        step="pipeline_queued",
    )

    try:
        submission.status = "PROCESSING"
        db.commit()

        mark_job_processing(
            db=db,
            job=job,
            step="extracting_text",
            progress=10,
        )

        analyze_job, extracted_document = analyze_submission_text(
            db=db,
            submission_id=submission_id,
        )

        mark_job_processing(
            db=db,
            job=analyze_job,
            step="detecting_reference_section",
            progress=35,
        )

        reference_job, reference_section = detect_and_save_reference_section(
            db=db,
            submission_id=submission_id,
        )

        mark_job_processing(
            db=db,
            job=reference_job,
            step="parsing_citations",
            progress=60,
        )

        citation_job, citations = parse_and_save_citations(
            db=db,
            submission_id=submission_id,
        )

        mark_job_processing(
            db=db,
            job=citation_job,
            step="verifying_metadata",
            progress=85,
        )

        metadata_job, metadata_records = verify_submission_metadata(
            db=db,
            submission_id=submission_id,
        )

        final_job = mark_job_completed(
            db=db,
            job=metadata_job,
            step="pipeline_completed",
        )

        submission.status = "REPORT_READY"
        db.commit()

        return {
            "message": "Chạy pipeline xử lý bài nộp thành công.",
            "submission_id": str(submission_id),
            "job": final_job,
            "result": {
                "extracted_document_id": str(extracted_document.id),
                "reference_section_id": str(reference_section.id),
                "citation_count": len(citations),
                "metadata_record_count": len(metadata_records),
            },
        }

    except HTTPException as exc:
        failed_job = get_latest_job_by_submission_id(
            db=db,
            submission_id=submission_id,
        ) or job

        mark_job_failed(
            db=db,
            job=failed_job,
            error_code="PIPELINE_FAILED",
        )

        submission.status = "PROCESSING_FAILED"
        db.commit()

        raise exc

    except Exception as exc:
        failed_job = get_latest_job_by_submission_id(
            db=db,
            submission_id=submission_id,
        ) or job

        mark_job_failed(
            db=db,
            job=failed_job,
            error_code="PIPELINE_FAILED",
        )

        submission.status = "PROCESSING_FAILED"
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "PIPELINE_FAILED",
                "message": "Pipeline xử lý bài nộp thất bại.",
                "details": {
                    "submission_id": str(submission_id),
                    "reason": str(exc),
                },
            },
        )


def retry_submission_processing_job(
    db: Session,
    job_id: UUID,
) -> dict[str, Any]:
    job = get_job_by_id(
        db=db,
        job_id=job_id,
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "JOB_NOT_FOUND",
                "message": "Không tìm thấy job xử lý.",
                "details": {
                    "job_id": str(job_id),
                },
            },
        )

    return run_submission_processing_pipeline(
        db=db,
        submission_id=job.submission_id,
    )