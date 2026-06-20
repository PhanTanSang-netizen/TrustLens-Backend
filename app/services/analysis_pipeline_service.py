from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.db.session import SessionLocal
from app.models.assignment import Assignment
from app.models.citation import Citation
from app.models.extracted_document import ExtractedDocument
from app.models.file import File as FileModel
from app.models.metadata_record import MetadataRecord
from app.models.processing_job import ProcessingJob
from app.models.reference_section import ReferenceSection
from app.models.report import Report
from app.models.submission import Submission
from app.processing.citation.citation_parser import parse_citations_from_reference_text
from app.processing.extraction.docx_extractor import extract_text_from_docx
from app.processing.extraction.pdf_extractor import extract_text_from_pdf
from app.processing.extraction.reference_detector import detect_reference_section
from app.services.audit_service import record_audit_log
from app.services.metadata_verification_service import verify_citation_metadata
from app.services.scoring_service import score_submission


class PipelineError(Exception):
    def __init__(self, status: str, error_code: str, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.error_code = error_code
        self.message = message
        self.details = details or {}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _set_job_state(db: Session, job: ProcessingJob, status_value: str, progress: int, current_step: str) -> None:
    job.status = status_value
    job.progress = progress
    job.step = current_step
    job.current_step = current_step
    job.updated_at = _utcnow()
    if job.started_at is None and status_value != "QUEUED":
        job.started_at = _utcnow()
    db.commit()


def _fail_job(db: Session, job: ProcessingJob, exc: PipelineError) -> None:
    job.status = exc.status
    job.current_step = exc.status.lower()
    job.step = job.current_step
    job.error_code = exc.error_code
    job.error_message = exc.message
    job.error_details = exc.details
    job.finished_at = _utcnow()
    job.updated_at = _utcnow()
    record_audit_log(db=db, user_id=job.created_by, action="ANALYSIS_FAILED", resource_type="processing_job", resource_id=str(job.id), message=exc.message, details={"error_code": exc.error_code, **exc.details})
    db.commit()


def _get_context(db: Session, job_id: UUID) -> tuple[ProcessingJob, Submission, FileModel, Assignment]:
    job = db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id)).scalar_one_or_none()
    if job is None:
        raise PipelineError("FAILED_INTERNAL", "JOB_NOT_FOUND", "Job no longer exists.")
    submission = db.execute(
        select(Submission)
        .options(joinedload(Submission.assignment).joinedload(Assignment.scoring_config))
        .where(Submission.id == job.submission_id)
    ).scalar_one_or_none()
    if submission is None:
        raise PipelineError("FAILED_INTERNAL", "SUBMISSION_NOT_FOUND", "Submission no longer exists.")
    file_record = db.execute(select(FileModel).where(FileModel.id == submission.file_id)).scalar_one_or_none()
    if file_record is None:
        raise PipelineError("FAILED_INTERNAL", "FILE_RECORD_NOT_FOUND", "File metadata no longer exists.")
    return job, submission, file_record, submission.assignment


def _extract(file_record: FileModel) -> tuple[str, int | None, int | None, str]:
    stored_path = Path(file_record.stored_path)
    if not stored_path.exists():
        raise PipelineError("FAILED_VALIDATION", "FILE_NOT_FOUND", "Uploaded file is missing.", {"stored_path": file_record.stored_path})
    try:
        if stored_path.suffix.lower() == ".docx":
            result = extract_text_from_docx(str(stored_path))
        elif stored_path.suffix.lower() == ".pdf":
            result = extract_text_from_pdf(str(stored_path))
        else:
            raise PipelineError("FAILED_VALIDATION", "UNSUPPORTED_FILE_TYPE", "Only PDF and DOCX files are supported.", {"extension": stored_path.suffix.lower()})
    except PipelineError:
        raise
    except Exception as exc:
        raise PipelineError("FAILED_EXTRACTION", "EXTRACTION_FAILED", "Could not extract text from file.", {"reason": str(exc)}) from exc
    if not result.full_text.strip():
        raise PipelineError("FAILED_EXTRACTION", "PDF_HAS_NO_TEXT_LAYER" if stored_path.suffix.lower() == ".pdf" else "EXTRACTED_TEXT_EMPTY", "File has no extractable text. OCR is not supported in MVP.", {"page_count": result.page_count})
    return result.full_text, result.page_count, result.word_count, result.extraction_method


def _build_report_context(full_text: str, reference_section: ReferenceSection, assignment: Assignment) -> dict:
    before_references = full_text[: reference_section.start_index]
    after_references = full_text[reference_section.end_index :]
    body_text = f"{before_references}\n{after_references}".strip()
    assignment_text = " ".join(part for part in [assignment.title, assignment.description] if part)
    scoring_text = f"{assignment_text}\n{body_text}".strip()
    return {
        "assignment_title": assignment.title,
        "assignment_description": assignment.description,
        "body_text": body_text,
        "scoring_text": scoring_text,
        "excluded_reference_section": {
            "start_index": reference_section.start_index,
            "end_index": reference_section.end_index,
            "heading": reference_section.heading,
        },
    }


def run_analysis_pipeline(job_id: str) -> None:
    db = SessionLocal()
    try:
        job, submission, file_record, assignment = _get_context(db, UUID(job_id))
        _set_job_state(db, job, "VALIDATING", 5, "validating")
        submission.status = "VALIDATING"
        db.commit()

        _set_job_state(db, job, "EXTRACTING", 15, "extracting")
        full_text, page_count, word_count, extraction_method = _extract(file_record)
        extracted_document = db.execute(select(ExtractedDocument).where(ExtractedDocument.submission_id == submission.id)).scalar_one_or_none()
        if extracted_document is None:
            extracted_document = ExtractedDocument(submission_id=submission.id, full_text=full_text, page_count=page_count, word_count=word_count, extraction_method=extraction_method, status="EXTRACTED")
            db.add(extracted_document)
        else:
            extracted_document.full_text = full_text
            extracted_document.page_count = page_count
            extracted_document.word_count = word_count
            extracted_document.extraction_method = extraction_method
            extracted_document.status = "EXTRACTED"
        submission.status = "TEXT_EXTRACTED"
        db.commit()

        _set_job_state(db, job, "DETECTING_REFERENCES", 30, "detecting_references")
        detected_section = detect_reference_section(full_text)
        if detected_section is None:
            raise PipelineError("FAILED_EXTRACTION", "NO_REFERENCE_SECTION", "No reference section found.", {"submission_id": str(submission.id)})
        reference_section = db.execute(select(ReferenceSection).where(ReferenceSection.submission_id == submission.id)).scalar_one_or_none()
        if reference_section is None:
            reference_section = ReferenceSection(submission_id=submission.id, heading=detected_section.heading, raw_text=detected_section.raw_text, start_index=detected_section.start_index, end_index=detected_section.end_index, detection_method=detected_section.detection_method)
            db.add(reference_section)
        else:
            reference_section.heading = detected_section.heading
            reference_section.raw_text = detected_section.raw_text
            reference_section.start_index = detected_section.start_index
            reference_section.end_index = detected_section.end_index
            reference_section.detection_method = detected_section.detection_method
        db.commit()

        _set_job_state(db, job, "PARSING_CITATIONS", 40, "parsing_citations")
        parsed_citations = parse_citations_from_reference_text(reference_section.raw_text)
        if not parsed_citations:
            raise PipelineError("FAILED_EXTRACTION", "CITATIONS_NOT_FOUND", "No citation entries were parsed.", {"submission_id": str(submission.id)})
        db.execute(delete(Citation).where(Citation.submission_id == submission.id))
        db.flush()
        citations = []
        for parsed in parsed_citations:
            citation = Citation(submission_id=submission.id, reference_section_id=reference_section.id, sequence_no=parsed.sequence_no, raw_text=parsed.raw_text, detected_style=parsed.detected_style, authors=parsed.authors, title=parsed.title, year=parsed.year, doi=parsed.doi, url=parsed.url)
            db.add(citation)
            citations.append(citation)
        submission.status = "CITATIONS_PARSED"
        db.commit()
        for citation in citations:
            db.refresh(citation)

        _set_job_state(db, job, "NORMALIZING", 50, "normalizing")
        _set_job_state(db, job, "VERIFYING_METADATA", 65, "verifying_metadata")
        db.execute(delete(MetadataRecord).where(MetadataRecord.submission_id == submission.id))
        metadata_records = []
        for index, citation in enumerate(citations, start=1):
            resolved = verify_citation_metadata(citation)
            record = MetadataRecord(
                submission_id=submission.id,
                citation_id=citation.id,
                provider=resolved.provider,
                query_type=resolved.query_type,
                query_value=resolved.query_value,
                source_url=resolved.source_url,
                matched_title=resolved.matched_title,
                matched_year=resolved.matched_year,
                verification_status=resolved.status.value,
                confidence_score=resolved.confidence_score,
                raw_response={
                    "citation_sequence_no": citation.sequence_no,
                    "citation_title": citation.title,
                    "citation_authors": citation.authors,
                    "citation_year": citation.year,
                    "citation_doi": citation.doi,
                    "citation_url": citation.url,
                    "matched_doi": resolved.matched_doi,
                    "matched_authors": resolved.matched_authors,
                    "abstract": resolved.abstract,
                    "venue": resolved.venue,
                    "publisher": resolved.publisher,
                    "source_type": resolved.source_type,
                    "citation_count": resolved.citation_count,
                    "publication_status": resolved.publication_status,
                    "is_retracted": resolved.is_retracted,
                    "retraction_sources": resolved.retraction_sources,
                    "publication_status_warnings": resolved.publication_status_warnings,
                    "candidate_count": resolved.candidate_count,
                    "candidate_margin": resolved.candidate_margin,
                    "evidence": resolved.evidence,
                    "provider_error": resolved.provider_error,
                    "raw_provider_response": resolved.raw_response,
                },
            )
            db.add(record)
            metadata_records.append(record)
            job.progress = min(75, 60 + int(index / max(1, len(citations)) * 15))
            db.flush()
        submission.status = "METADATA_VERIFIED"
        db.commit()
        for record in metadata_records:
            db.refresh(record)

        _set_job_state(db, job, "SCORING", 80, "scoring")
        report_context = _build_report_context(full_text, reference_section, assignment)
        scoring_result = score_submission(
            db=db,
            submission_id=submission.id,
            citations=citations,
            metadata_records=metadata_records,
            report_context=report_context,
            scoring_config=assignment.scoring_config,
            expected_style=assignment.required_style,
        )
        submission.overall_score = scoring_result["report_trust_score"]
        submission.status = "SCORED"
        db.commit()

        _set_job_state(db, job, "BUILDING_REPORT", 90, "building_report")
        report = db.execute(select(Report).where(Report.submission_id == submission.id)).scalar_one_or_none()
        if report is None:
            report = Report(submission_id=submission.id)
            db.add(report)
            db.flush()
        report.job_id = job.id
        report.scoring_config_version = scoring_result["scoring_config_version"]
        report.report_trust_score = scoring_result["report_trust_score"]
        report.confidence_score = scoring_result["confidence_score"]
        report.overall_label = scoring_result["overall_label"]
        report.report_penalty = scoring_result["report_penalty"]["total"]
        report.summary = scoring_result["summary"]
        report.component_summary = scoring_result["component_summary"]
        report.citations_payload = scoring_result["citations"]
        report.warnings = scoring_result["warnings"]
        report.updated_at = _utcnow()
        job.status = "COMPLETED"
        job.progress = 100
        job.step = "completed"
        job.current_step = "completed"
        job.report_id = report.id
        job.error_code = None
        job.error_message = None
        job.error_details = None
        job.finished_at = _utcnow()
        job.updated_at = _utcnow()
        submission.status = "COMPLETED"
        record_audit_log(db=db, user_id=job.created_by, action="ANALYSIS_COMPLETED", resource_type="submission", resource_id=str(submission.id), message="Analysis completed.", details={"report_id": str(report.id)})
        db.commit()
    except PipelineError as exc:
        db.rollback()
        job = db.execute(select(ProcessingJob).where(ProcessingJob.id == UUID(job_id))).scalar_one_or_none()
        if job is not None:
            _fail_job(db, job, exc)
    except Exception as exc:
        db.rollback()
        job = db.execute(select(ProcessingJob).where(ProcessingJob.id == UUID(job_id))).scalar_one_or_none()
        if job is not None:
            _fail_job(db, job, PipelineError("FAILED_INTERNAL", "INTERNAL_ERROR", "Unexpected analysis pipeline failure.", {"reason": str(exc)}))
    finally:
        db.close()
