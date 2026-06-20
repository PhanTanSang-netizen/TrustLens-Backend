from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.citation import Citation
from app.models.processing_job import ProcessingJob
from app.models.reference_section import ReferenceSection
from app.models.submission import Submission
from app.processing.citation.citation_normalizer import normalize_citation_fields
from app.processing.citation.citation_parser import parse_citations_from_reference_text


def get_submission_by_id(
    db: Session,
    submission_id: UUID,
) -> Submission | None:
    return db.execute(
        select(Submission).where(Submission.id == submission_id)
    ).scalar_one_or_none()


def get_reference_section_by_submission_id(
    db: Session,
    submission_id: UUID,
) -> ReferenceSection | None:
    return db.execute(
        select(ReferenceSection).where(
            ReferenceSection.submission_id == submission_id
        )
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


def parse_and_save_citations(
    db: Session,
    submission_id: UUID,
) -> tuple[ProcessingJob, list[Citation]]:
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

    reference_section = get_reference_section_by_submission_id(
        db=db,
        submission_id=submission_id,
    )

    if reference_section is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "REFERENCE_SECTION_NOT_FOUND",
                "message": "Chưa có phần tài liệu tham khảo. Hãy chạy detect-references trước.",
                "details": {
                    "submission_id": str(submission_id),
                },
            },
        )

    try:
        parsed_citations = parse_citations_from_reference_text(
            raw_text=reference_section.raw_text,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "CITATION_PARSE_FAILED",
                "message": "Không thể tách citation từ phần tài liệu tham khảo.",
                "details": {
                    "submission_id": str(submission_id),
                    "reason": str(exc),
                },
            },
        ) from exc

    if not parsed_citations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "CITATIONS_NOT_FOUND",
                "message": "Không tách được citation nào từ phần tài liệu tham khảo.",
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
    job.progress = 75
    job.step = "parsing_citations"
    db.flush()

    db.execute(
        delete(Citation).where(
            Citation.submission_id == submission_id
        )
    )

    citation_records: list[Citation] = []

    for parsed_citation in parsed_citations:
        normalized_fields = normalize_citation_fields(
            raw_text=parsed_citation.raw_text,
            authors=parsed_citation.authors,
            title=parsed_citation.title,
            year=parsed_citation.year,
            doi=parsed_citation.doi,
            url=parsed_citation.url,
        )

        citation = Citation(
            submission_id=submission_id,
            reference_section_id=reference_section.id,
            sequence_no=parsed_citation.sequence_no,
            raw_text=normalized_fields.raw_text,
            detected_style=parsed_citation.detected_style,
            authors=normalized_fields.authors,
            title=normalized_fields.title,
            year=normalized_fields.year,
            doi=normalized_fields.doi,
            url=normalized_fields.url,
        )

        db.add(citation)
        citation_records.append(citation)

    submission.status = "CITATIONS_PARSED"

    job.status = "COMPLETED"
    job.progress = 100
    job.step = "citations_parsed"
    job.error_code = None

    db.commit()
    db.refresh(job)

    for citation in citation_records:
        db.refresh(citation)

    return job, citation_records