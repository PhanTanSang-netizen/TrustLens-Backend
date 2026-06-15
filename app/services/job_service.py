from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.processing_job import ProcessingJob


def get_job_by_id(
    db: Session,
    job_id: UUID,
) -> ProcessingJob | None:
    return db.execute(
        select(ProcessingJob).where(ProcessingJob.id == job_id)
    ).scalar_one_or_none()