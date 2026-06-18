from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.citation import Citation
from app.models.extracted_document import ExtractedDocument
from app.models.file import File as FileModel
from app.models.metadata_record import MetadataRecord
from app.models.processing_job import ProcessingJob
from app.models.reference_section import ReferenceSection
from app.models.submission import Submission


def _json_safe(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    return value


def _get_attr(obj: Any, field_name: str, default: Any = None) -> Any:
    if obj is None:
        return default

    return getattr(obj, field_name, default)


def get_submission_by_id(
    db: Session,
    submission_id: UUID,
) -> Submission | None:
    return db.execute(
        select(Submission).where(Submission.id == submission_id)
    ).scalar_one_or_none()


def get_file_by_id(
    db: Session,
    file_id: UUID,
) -> FileModel | None:
    return db.execute(
        select(FileModel).where(FileModel.id == file_id)
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


def get_metadata_records_by_submission_id(
    db: Session,
    submission_id: UUID,
) -> list[MetadataRecord]:
    return list(
        db.execute(
            select(MetadataRecord)
            .where(MetadataRecord.submission_id == submission_id)
            .order_by(MetadataRecord.created_at.asc())
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


def build_verification_summary(
    metadata_records: list[MetadataRecord],
) -> dict[str, int]:
    verified = len([
        record
        for record in metadata_records
        if record.verification_status in [
            "URL_OK",
            "DOI_OK",
        ]
    ])

    basic_metadata_present = len([
        record
        for record in metadata_records
        if record.verification_status == "BASIC_METADATA_PRESENT"
    ])

    broken = len([
        record
        for record in metadata_records
        if record.verification_status == "URL_BROKEN"
    ])

    forbidden = len([
        record
        for record in metadata_records
        if record.verification_status == "URL_FORBIDDEN"
    ])

    unreachable = len([
        record
        for record in metadata_records
        if record.verification_status in [
            "URL_UNREACHABLE",
            "DOI_UNREACHABLE",
        ]
    ])

    not_provided = len([
        record
        for record in metadata_records
        if record.verification_status in [
            "URL_NOT_PROVIDED",
            "METADATA_NOT_PROVIDED",
        ]
    ])

    return {
        "total": len(metadata_records),
        "verified": verified,
        "basic_metadata_present": basic_metadata_present,
        "broken": broken,
        "forbidden": forbidden,
        "unreachable": unreachable,
        "not_provided": not_provided,
    }


def build_processing_summary(
    submission: Submission,
    extracted_document: ExtractedDocument | None,
    reference_section: ReferenceSection | None,
    citations: list[Citation],
    metadata_records: list[MetadataRecord],
    latest_job: ProcessingJob | None,
) -> dict[str, Any]:
    return {
        "submission_status": _get_attr(submission, "status"),
        "has_extracted_text": extracted_document is not None,
        "has_reference_section": reference_section is not None,
        "citation_count": len(citations),
        "metadata_record_count": len(metadata_records),
        "latest_job": {
            "id": _json_safe(_get_attr(latest_job, "id")),
            "status": _get_attr(latest_job, "status"),
            "progress": _get_attr(latest_job, "progress"),
            "step": _get_attr(latest_job, "step"),
            "error_code": _get_attr(latest_job, "error_code"),
            "created_at": _json_safe(_get_attr(latest_job, "created_at")),
            "updated_at": _json_safe(_get_attr(latest_job, "updated_at")),
        } if latest_job is not None else None,
    }


def build_metadata_by_citation_id(
    metadata_records: list[MetadataRecord],
) -> dict[str, MetadataRecord]:
    result: dict[str, MetadataRecord] = {}

    for record in metadata_records:
        citation_id = _get_attr(record, "citation_id")

        if citation_id is not None:
            result[str(citation_id)] = record

    return result


def build_citation_warnings(
    citation: Citation,
    metadata_record: MetadataRecord | None,
) -> list[str]:
    warnings: list[str] = []

    if not _get_attr(citation, "title"):
        warnings.append("MISSING_TITLE")

    if not _get_attr(citation, "authors"):
        warnings.append("MISSING_AUTHORS")

    if not _get_attr(citation, "year"):
        warnings.append("MISSING_YEAR")

    if not _get_attr(citation, "doi") and not _get_attr(citation, "url"):
        warnings.append("MISSING_DOI_OR_URL")

    if _get_attr(citation, "detected_style") == "UNKNOWN":
        warnings.append("UNKNOWN_CITATION_STYLE")

    verification_status = _get_attr(
        metadata_record,
        "verification_status",
    )

    if verification_status in [
        "URL_BROKEN",
        "URL_UNREACHABLE",
        "DOI_UNREACHABLE",
        "METADATA_NOT_PROVIDED",
    ]:
        warnings.append(verification_status)

    if verification_status == "URL_FORBIDDEN":
        warnings.append("URL_BLOCKS_AUTOMATED_CHECK")

    return warnings


def build_citation_items(
    citations: list[Citation],
    metadata_records: list[MetadataRecord],
) -> list[dict[str, Any]]:
    metadata_by_citation_id = build_metadata_by_citation_id(
        metadata_records=metadata_records,
    )

    items: list[dict[str, Any]] = []

    for citation in citations:
        citation_id = str(_get_attr(citation, "id"))
        metadata_record = metadata_by_citation_id.get(citation_id)

        items.append(
            {
                "citation": {
                    "id": citation_id,
                    "sequence_no": _get_attr(citation, "sequence_no"),
                    "raw_text": _get_attr(citation, "raw_text"),
                    "detected_style": _get_attr(citation, "detected_style"),
                    "authors": _get_attr(citation, "authors"),
                    "title": _get_attr(citation, "title"),
                    "year": _get_attr(citation, "year"),
                    "doi": _get_attr(citation, "doi"),
                    "url": _get_attr(citation, "url"),
                },
                "metadata": {
                    "id": _json_safe(_get_attr(metadata_record, "id")),
                    "provider": _get_attr(metadata_record, "provider"),
                    "query_type": _get_attr(metadata_record, "query_type"),
                    "query_value": _get_attr(metadata_record, "query_value"),
                    "source_url": _get_attr(metadata_record, "source_url"),
                    "matched_title": _get_attr(metadata_record, "matched_title"),
                    "matched_year": _get_attr(metadata_record, "matched_year"),
                    "verification_status": _get_attr(
                        metadata_record,
                        "verification_status",
                        "NOT_VERIFIED",
                    ),
                    "confidence_score": _get_attr(
                        metadata_record,
                        "confidence_score",
                        0.0,
                    ),
                    "raw_response": _get_attr(metadata_record, "raw_response"),
                },
                "warnings": build_citation_warnings(
                    citation=citation,
                    metadata_record=metadata_record,
                ),
                "score": None,
                "trust_level": "NOT_CALCULATED",
            }
        )

    return items


def get_submission_report(
    db: Session,
    submission_id: UUID,
) -> dict[str, Any]:
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

    file_record = get_file_by_id(
        db=db,
        file_id=submission.file_id,
    )

    extracted_document = get_extracted_document_by_submission_id(
        db=db,
        submission_id=submission_id,
    )

    reference_section = get_reference_section_by_submission_id(
        db=db,
        submission_id=submission_id,
    )

    citations = get_citations_by_submission_id(
        db=db,
        submission_id=submission_id,
    )

    metadata_records = get_metadata_records_by_submission_id(
        db=db,
        submission_id=submission_id,
    )

    latest_job = get_latest_job_by_submission_id(
        db=db,
        submission_id=submission_id,
    )

    verification_summary = build_verification_summary(
        metadata_records=metadata_records,
    )

    citation_items = build_citation_items(
        citations=citations,
        metadata_records=metadata_records,
    )

    processing_summary = build_processing_summary(
        submission=submission,
        extracted_document=extracted_document,
        reference_section=reference_section,
        citations=citations,
        metadata_records=metadata_records,
        latest_job=latest_job,
    )

    return {
        "message": "Tạo báo cáo thẩm định thành công.",
        "submission": {
            "id": _json_safe(_get_attr(submission, "id")),
            "assignment_id": _json_safe(_get_attr(submission, "assignment_id")),
            "file_id": _json_safe(_get_attr(submission, "file_id")),
            "owner_label": _get_attr(submission, "owner_label"),
            "status": _get_attr(submission, "status"),
            "overall_score": _get_attr(submission, "overall_score"),
            "created_at": _json_safe(_get_attr(submission, "created_at")),
            "updated_at": _json_safe(_get_attr(submission, "updated_at")),
        },
        "file": {
            "id": _json_safe(_get_attr(file_record, "id")),
            "original_name": _get_attr(file_record, "original_name"),
            "stored_name": _get_attr(file_record, "stored_name"),
            "mime_type": _get_attr(file_record, "mime_type"),
            "size_bytes": _get_attr(file_record, "size_bytes"),
            "checksum": _get_attr(file_record, "checksum"),
            "uploaded_by": _json_safe(_get_attr(file_record, "uploaded_by")),
            "created_at": _json_safe(_get_attr(file_record, "created_at")),
        } if file_record is not None else None,
        "extracted_document": {
            "id": _json_safe(_get_attr(extracted_document, "id")),
            "word_count": _get_attr(extracted_document, "word_count"),
            "page_count": _get_attr(extracted_document, "page_count"),
            "extraction_method": _get_attr(extracted_document, "extraction_method"),
            "status": _get_attr(extracted_document, "status"),
            "created_at": _json_safe(_get_attr(extracted_document, "created_at")),
        } if extracted_document is not None else None,
        "reference_section": {
            "id": _json_safe(_get_attr(reference_section, "id")),
            "heading": _get_attr(reference_section, "heading"),
            "start_index": _get_attr(reference_section, "start_index"),
            "end_index": _get_attr(reference_section, "end_index"),
            "detection_method": _get_attr(reference_section, "detection_method"),
            "raw_text_preview": (
                (_get_attr(reference_section, "raw_text", "") or "")[:800]
            ),
        } if reference_section is not None else None,
        "summary": {
            "processing": processing_summary,
            "verification": verification_summary,
            "score": {
                "overall_score": None,
                "trust_level": "NOT_CALCULATED",
                "note": "Scoring module is not enabled in this MVP report yet.",
            },
        },
        "citations": citation_items,
    }


def build_submission_report(
    db: Session,
    submission_id: UUID,
) -> dict[str, Any]:
    return get_submission_report(
        db=db,
        submission_id=submission_id,
    )


def generate_submission_report(
    db: Session,
    submission_id: UUID,
) -> dict[str, Any]:
    return get_submission_report(
        db=db,
        submission_id=submission_id,
    )


def get_report_by_submission_id(
    db: Session,
    submission_id: UUID,
) -> dict[str, Any]:
    return get_submission_report(
        db=db,
        submission_id=submission_id,
    )