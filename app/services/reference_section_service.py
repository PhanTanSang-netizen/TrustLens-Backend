from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.extracted_document import ExtractedDocument
from app.models.processing_job import ProcessingJob
from app.models.reference_section import ReferenceSection
from app.models.submission import Submission
from app.processing.extraction.reference_detector import detect_reference_section


def get_submission_by_id(
    db: Session,
    submission_id: UUID,
) -> Submission | None:
    return db.execute(
        select(Submission).where(Submission.id == submission_id)
    ).scalar_one_or_none()


def get_extracted_document_by_submission_id(
    db: Session,
    submission_id: UUID,
) -> ExtractedDocument | None:
    return db.execute(
        select(ExtractedDocument).where(
            ExtractedDocument.submission_id == submission_id
        )
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


def detect_and_save_reference_section(
    db: Session,
    submission_id: UUID,
) -> tuple[ProcessingJob, ReferenceSection]:
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

    extracted_document = get_extracted_document_by_submission_id(
        db=db,
        submission_id=submission_id,
    )

    if extracted_document is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "TEXT_NOT_EXTRACTED",
                "message": "Tài liệu chưa được trích xuất text. Hãy chạy analyze trước.",
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
    job.progress = 60
    job.step = "detecting_reference_section"
    db.flush()

    detected_section = detect_reference_section(
        full_text=extracted_document.full_text,
    )

    if detected_section is None:
        job.status = "FAILED"
        job.progress = 100
        job.step = "reference_section_not_found"
        job.error_code = "REFERENCE_SECTION_NOT_FOUND"
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "REFERENCE_SECTION_NOT_FOUND",
                "message": "Không tìm thấy phần tài liệu tham khảo trong văn bản.",
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
        reference_section = ReferenceSection(
            submission_id=submission_id,
            heading=detected_section.heading,
            raw_text=detected_section.raw_text,
            start_index=detected_section.start_index,
            end_index=detected_section.end_index,
            detection_method=detected_section.detection_method,
        )
        db.add(reference_section)

    else:
        reference_section.heading = detected_section.heading
        reference_section.raw_text = detected_section.raw_text
        reference_section.start_index = detected_section.start_index
        reference_section.end_index = detected_section.end_index
        reference_section.detection_method = detected_section.detection_method

    submission.status = "REFERENCE_SECTION_DETECTED"

    job.status = "COMPLETED"
    job.progress = 100
    job.step = "reference_section_detected"
    job.error_code = None

    db.commit()
    db.refresh(job)
    db.refresh(reference_section)

    return job, reference_section