from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.processing_job import ProcessingJob
from app.models.report import Report


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


def get_job_by_id(
    db: Session,
    job_id: UUID,
) -> ProcessingJob | None:
    return db.execute(
        select(ProcessingJob).where(ProcessingJob.id == job_id)
    ).scalar_one_or_none()


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
