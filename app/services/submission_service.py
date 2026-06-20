from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.file import File as FileModel
from app.models.processing_job import ProcessingJob
from app.models.submission import Submission
from app.services.file_storage_service import StoredFileData


def get_assignment_by_id(
    db: Session,
    assignment_id: UUID,
) -> Assignment | None:
    return db.execute(
        select(Assignment).where(Assignment.id == assignment_id)
    ).scalar_one_or_none()


def create_submission_with_file_and_job(
    db: Session,
    assignment_id: UUID,
    owner_label: str | None,
    stored_file: StoredFileData,
    uploaded_by: UUID,
) -> tuple[Submission, FileModel, ProcessingJob]:
    db_file = FileModel(
        original_name=stored_file.original_name,
        stored_name=stored_file.stored_name,
        stored_path=stored_file.stored_path,
        mime_type=stored_file.mime_type,
        size_bytes=stored_file.size_bytes,
        checksum=stored_file.checksum,
        uploaded_by=uploaded_by,
    )

    db.add(db_file)
    db.flush()

    submission = Submission(
        assignment_id=assignment_id,
        file_id=db_file.id,
        owner_label=owner_label,
        status="UPLOADED",
        overall_score=None,
    )

    db.add(submission)
    db.flush()

    job = ProcessingJob(
        submission_id=submission.id,
        status="QUEUED",
        progress=0,
        step="queued",
        current_step="queued",
        error_code=None,
        created_by=uploaded_by,
    )

    db.add(job)

    db.commit()

    db.refresh(db_file)
    db.refresh(submission)
    db.refresh(job)

    return submission, db_file, job
