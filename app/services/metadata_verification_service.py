from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.citation import Citation
from app.models.metadata_record import MetadataRecord
from app.models.processing_job import ProcessingJob
from app.models.submission import Submission
from app.processing.metadata.url_checker import check_url_exists


def get_submission_by_id(
    db: Session,
    submission_id: UUID,
) -> Submission | None:
    return db.execute(
        select(Submission).where(Submission.id == submission_id)
    ).scalar_one_or_none()


def get_citations_by_submission_id(
    db: Session,
    submission_id: UUID,
) -> list[Citation]:
    return list(
        db.execute(
            select(Citation)
            .where(Citation.submission_id == submission_id)
            .order_by(Citation.sequence_no.asc())
        ).scalars().all()
    )


def get_latest_job_by_submission_id(
    db: Session,
    submission_id: UUID,
) -> ProcessingJob | None:
    return db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.submission_id == submission_id)
        .order_by(ProcessingJob.created_at.desc())
    ).scalars().first()


def verify_submission_metadata(
    db: Session,
    submission_id: UUID,
) -> tuple[ProcessingJob, list[MetadataRecord]]:
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

    citations = get_citations_by_submission_id(
        db=db,
        submission_id=submission_id,
    )

    if not citations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "CITATIONS_NOT_FOUND",
                "message": "Chưa có citation. Hãy chạy parse-citations trước.",
                "details": {
                    "submission_id": str(submission_id),
                },
            },
        )

    job = get_latest_job_by_submission_id(
        db=db,
        submission_id=submission_id,
    )

    if job is None:
        job = ProcessingJob(
            submission_id=submission_id,
            status="QUEUED",
            progress=0,
            step="queued",
        )
        db.add(job)
        db.flush()

    job.status = "PROCESSING"
    job.progress = 85
    job.step = "verifying_metadata"
    db.flush()

    db.execute(
        delete(MetadataRecord).where(
            MetadataRecord.submission_id == submission_id
        )
    )

    metadata_records: list[MetadataRecord] = []

    for citation in citations:
        url_check = check_url_exists(citation.url)

        record = MetadataRecord(
            submission_id=submission_id,
            citation_id=citation.id,
            provider="URL_CHECK",
            query_type="url",
            query_value=citation.url,
            source_url=url_check.final_url,
            matched_title=citation.title,
            matched_year=citation.year,
            verification_status=url_check.verification_status,
            confidence_score=url_check.confidence_score,
            raw_response={
                "citation_sequence_no": citation.sequence_no,
                "citation_title": citation.title,
                "citation_url": citation.url,
                "status_code": url_check.status_code,
                "final_url": url_check.final_url,
                "error": url_check.error,
            },
        )

        db.add(record)
        metadata_records.append(record)

    submission.status = "METADATA_VERIFIED"

    job.status = "COMPLETED"
    job.progress = 100
    job.step = "metadata_verified"
    job.error_code = None

    db.commit()
    db.refresh(job)

    for record in metadata_records:
        db.refresh(record)

    return job, metadata_records