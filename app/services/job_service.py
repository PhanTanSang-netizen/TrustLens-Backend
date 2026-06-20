from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.processing_job import ProcessingJob
from app.models.report import Report
from app.models.submission import Submission


ACTIVE_JOB_STATUSES = {
    "QUEUED",
    "VALIDATING",
    "EXTRACTING",
    "DETECTING_REFERENCES",
    "PARSING_CITATIONS",
    "NORMALIZING",
    "VERIFYING_METADATA",
    "SCORING",
    "BUILDING_REPORT",
}

NON_RETRYABLE_ERROR_PREFIXES = (
    "FILE_",
    "PDF_",
    "NO_REFERENCE",
    "UNSUPPORTED_FILE_TYPE",
)


def get_job_by_id(
    db: Session,
    job_id: UUID,
) -> ProcessingJob | None:
    return db.execute(
        select(ProcessingJob).where(ProcessingJob.id == job_id)
    ).scalar_one_or_none()


def get_submission_by_id(db: Session, submission_id: UUID) -> Submission | None:
    return db.execute(
        select(Submission).where(Submission.id == submission_id)
    ).scalar_one_or_none()


def get_latest_job_by_submission_id(db: Session, submission_id: UUID) -> ProcessingJob | None:
    return db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.submission_id == submission_id)
        .order_by(ProcessingJob.created_at.desc())
    ).scalars().first()


def get_active_job_for_submission(db: Session, submission_id: UUID) -> ProcessingJob | None:
    return db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.submission_id == submission_id, ProcessingJob.status.in_(ACTIVE_JOB_STATUSES))
        .order_by(ProcessingJob.created_at.desc())
    ).scalars().first()


def get_report_by_submission_id(db: Session, submission_id: UUID) -> Report | None:
    return db.execute(select(Report).where(Report.submission_id == submission_id)).scalar_one_or_none()


def create_queued_job(
    db: Session,
    submission_id: UUID,
    created_by: UUID | None,
    retry_of_job_id: UUID | None = None,
) -> ProcessingJob:
    job = ProcessingJob(
        submission_id=submission_id,
        status="QUEUED",
        progress=0,
        step="queued",
        current_step="queued",
        created_by=created_by,
        retry_of_job_id=retry_of_job_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def run_submission_processing_pipeline(
    db: Session,
    submission_id: UUID,
    created_by: UUID | None = None,
) -> ProcessingJob:
    submission = get_submission_by_id(db=db, submission_id=submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "SUBMISSION_NOT_FOUND",
                "message": "Submission not found.",
                "details": {"submission_id": str(submission_id)},
            },
        )

    active_job = get_active_job_for_submission(db=db, submission_id=submission_id)
    if active_job is not None:
        return active_job

    if get_report_by_submission_id(db=db, submission_id=submission_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "ANALYSIS_ALREADY_COMPLETED",
                "message": "Analysis has already completed for this submission.",
                "details": {"submission_id": str(submission_id)},
            },
        )

    return create_queued_job(
        db=db,
        submission_id=submission.id,
        created_by=created_by,
    )


def retry_submission_processing_job(
    db: Session,
    job_id: UUID,
    created_by: UUID | None = None,
) -> ProcessingJob:
    job = get_job_by_id(db=db, job_id=job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "JOB_NOT_FOUND",
                "message": "Job not found.",
                "details": {"job_id": str(job_id)},
            },
        )

    if job.status in ACTIVE_JOB_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "JOB_STILL_ACTIVE",
                "message": "Job is still running and cannot be retried yet.",
                "details": {"job_id": str(job_id), "status": job.status},
            },
        )

    if job.status == "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "JOB_ALREADY_COMPLETED",
                "message": "Completed jobs do not need retry.",
                "details": {"job_id": str(job_id)},
            },
        )

    if job.error_code and str(job.error_code).startswith(NON_RETRYABLE_ERROR_PREFIXES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "JOB_NOT_RETRYABLE",
                "message": "This job failure is not retryable.",
                "details": {"job_id": str(job_id), "error_code": job.error_code},
            },
        )

    active_job = get_active_job_for_submission(db=db, submission_id=job.submission_id)
    if active_job is not None:
        return active_job

    return create_queued_job(
        db=db,
        submission_id=job.submission_id,
        created_by=created_by,
        retry_of_job_id=job.id,
    )
