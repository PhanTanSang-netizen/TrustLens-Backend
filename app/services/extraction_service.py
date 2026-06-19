from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.extracted_document import ExtractedDocument
from app.models.file import File as FileModel
from app.models.processing_job import ProcessingJob
from app.models.submission import Submission
from app.processing.extraction.docx_extractor import extract_text_from_docx
from app.processing.extraction.pdf_extractor import extract_text_from_pdf


def get_submission_by_id(db: Session, submission_id: UUID) -> Submission | None:
    return db.execute(select(Submission).where(Submission.id == submission_id)).scalar_one_or_none()


def get_file_by_id(db: Session, file_id: UUID) -> FileModel | None:
    return db.execute(select(FileModel).where(FileModel.id == file_id)).scalar_one_or_none()


def get_latest_job_by_submission_id(db: Session, submission_id: UUID) -> ProcessingJob | None:
    return db.execute(select(ProcessingJob).where(ProcessingJob.submission_id == submission_id).order_by(ProcessingJob.created_at.desc())).scalars().first()


def get_extracted_document_by_submission_id(db: Session, submission_id: UUID) -> ExtractedDocument | None:
    return db.execute(select(ExtractedDocument).where(ExtractedDocument.submission_id == submission_id)).scalar_one_or_none()


def analyze_submission_text(db: Session, submission_id: UUID) -> tuple[ProcessingJob, ExtractedDocument]:
    submission = get_submission_by_id(db=db, submission_id=submission_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error_code": "SUBMISSION_NOT_FOUND", "message": "Submission not found.", "details": {"submission_id": str(submission_id)}})
    file_record = get_file_by_id(db=db, file_id=submission.file_id)
    if file_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error_code": "FILE_RECORD_NOT_FOUND", "message": "Submission file metadata not found.", "details": {"file_id": str(submission.file_id)}})
    job = get_latest_job_by_submission_id(db=db, submission_id=submission_id)
    if job is None:
        job = ProcessingJob(submission_id=submission_id, status="QUEUED", progress=0, step="queued", current_step="queued")
        db.add(job)
        db.flush()
    job.status = "PROCESSING"
    job.progress = 10
    job.step = "extracting_text"
    job.current_step = "extracting"
    db.flush()
    stored_path = Path(file_record.stored_path)
    try:
        if stored_path.suffix.lower() == ".docx":
            extracted_result = extract_text_from_docx(str(stored_path))
        elif stored_path.suffix.lower() == ".pdf":
            extracted_result = extract_text_from_pdf(str(stored_path))
            if not extracted_result.full_text.strip():
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"error_code": "PDF_HAS_NO_TEXT_LAYER", "message": "PDF does not contain extractable text. OCR is not supported in MVP.", "details": {"page_count": extracted_result.page_count}})
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error_code": "EXTRACTION_FORMAT_NOT_SUPPORTED", "message": "Only DOCX and PDF extraction are supported.", "details": {"stored_path": file_record.stored_path, "extension": stored_path.suffix.lower()}})
        extracted_document = get_extracted_document_by_submission_id(db=db, submission_id=submission_id)
        if extracted_document is None:
            extracted_document = ExtractedDocument(submission_id=submission_id, full_text=extracted_result.full_text, page_count=extracted_result.page_count, word_count=extracted_result.word_count, extraction_method=extracted_result.extraction_method, status="EXTRACTED")
            db.add(extracted_document)
        else:
            extracted_document.full_text = extracted_result.full_text
            extracted_document.page_count = extracted_result.page_count
            extracted_document.word_count = extracted_result.word_count
            extracted_document.extraction_method = extracted_result.extraction_method
            extracted_document.status = "EXTRACTED"
        submission.status = "TEXT_EXTRACTED"
        job.status = "COMPLETED"
        job.progress = 100
        job.step = "text_extracted"
        job.current_step = "completed"
        job.error_code = None
        db.commit()
        db.refresh(job)
        db.refresh(extracted_document)
        return job, extracted_document
    except HTTPException:
        job.status = "FAILED"
        job.progress = 100
        job.step = "failed"
        job.current_step = "failed"
        job.error_code = "EXTRACTION_FAILED"
        db.commit()
        raise
    except Exception as exc:
        job.status = "FAILED"
        job.progress = 100
        job.step = "failed"
        job.current_step = "failed"
        job.error_code = "EXTRACTION_FAILED"
        db.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error_code": "EXTRACTION_FAILED", "message": "Could not extract text from file.", "details": {"reason": str(exc)}})
