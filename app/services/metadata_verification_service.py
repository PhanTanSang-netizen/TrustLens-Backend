from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.citation import Citation
from app.models.metadata_record import MetadataRecord
from app.models.processing_job import ProcessingJob
from app.models.submission import Submission
from app.processing.metadata.crossref_client import (
    lookup_crossref_by_doi,
    search_crossref_by_title,
)
from app.processing.metadata.metadata_matcher import (
    MetadataCandidate,
    MetadataMatchResult,
    select_best_metadata_match,
)
from app.processing.metadata.openalex_client import search_openalex_by_title
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


def _build_record_from_academic_match(
    submission_id: UUID,
    citation: Citation,
    match_result: MetadataMatchResult,
) -> MetadataRecord:
    return MetadataRecord(
        submission_id=submission_id,
        citation_id=citation.id,
        provider=match_result.provider,
        query_type="doi" if citation.doi else "title_author_year",
        query_value=citation.doi or citation.title,
        source_url=match_result.source_url,
        matched_title=match_result.matched_title,
        matched_year=match_result.matched_year,
        verification_status=match_result.match_status,
        confidence_score=match_result.confidence_score,
        raw_response={
            "citation_sequence_no": citation.sequence_no,
            "citation_title": citation.title,
            "citation_authors": citation.authors,
            "citation_year": citation.year,
            "citation_doi": citation.doi,
            "citation_url": citation.url,
            "matched_doi": match_result.matched_doi,
            "matched_authors": match_result.matched_authors,
            "venue": match_result.venue,
            "publisher": match_result.publisher,
            "source_type": match_result.source_type,
            "credibility_explanation": match_result.credibility_explanation,
            "citation_signal": match_result.citation_signal,
            "raw_provider_response": match_result.raw_response,
        },
    )


def _build_record_from_url_fallback(
    submission_id: UUID,
    citation: Citation,
) -> MetadataRecord:
    provider = "BASIC_CHECK"
    query_type = "none"
    query_value = None
    source_url = None
    verification_status = "METADATA_NOT_PROVIDED"
    confidence_score = 0.0

    raw_response = {
        "citation_sequence_no": citation.sequence_no,
        "citation_title": citation.title,
        "citation_authors": citation.authors,
        "citation_year": citation.year,
        "citation_doi": citation.doi,
        "citation_url": citation.url,
    }

    if citation.doi:
        doi_url = f"https://doi.org/{citation.doi}"
        url_check = check_url_exists(doi_url)

        provider = "DOI_CHECK"
        query_type = "doi"
        query_value = citation.doi
        source_url = url_check.final_url
        verification_status = (
            "DOI_UNREACHABLE"
            if url_check.verification_status != "URL_OK"
            else "DOI_OK"
        )
        confidence_score = url_check.confidence_score

        raw_response.update(
            {
                "checked_url": doi_url,
                "status_code": url_check.status_code,
                "final_url": url_check.final_url,
                "error": url_check.error,
            }
        )

    elif citation.url:
        url_check = check_url_exists(citation.url)

        provider = "URL_CHECK"
        query_type = "url"
        query_value = citation.url
        source_url = url_check.final_url
        verification_status = url_check.verification_status
        confidence_score = url_check.confidence_score

        raw_response.update(
            {
                "checked_url": citation.url,
                "status_code": url_check.status_code,
                "final_url": url_check.final_url,
                "error": url_check.error,
            }
        )

    elif citation.title or citation.year:
        provider = "BASIC_METADATA_CHECK"
        query_type = "title_year"
        query_value = citation.title
        verification_status = "BASIC_METADATA_PRESENT"
        confidence_score = 0.35

        raw_response.update(
            {
                "reason": "Citation has title/year but no DOI or URL.",
            }
        )

    return MetadataRecord(
        submission_id=submission_id,
        citation_id=citation.id,
        provider=provider,
        query_type=query_type,
        query_value=query_value,
        source_url=source_url,
        matched_title=citation.title,
        matched_year=citation.year,
        verification_status=verification_status,
        confidence_score=confidence_score,
        raw_response=raw_response,
    )


def _find_academic_metadata_match(
    citation: Citation,
) -> MetadataMatchResult | None:
    candidates: list[MetadataCandidate] = []

    if citation.doi:
        crossref_candidate = lookup_crossref_by_doi(citation.doi)

        if crossref_candidate is not None:
            candidates.append(crossref_candidate)

    if citation.title:
        candidates.extend(
            search_crossref_by_title(
                title=citation.title,
                year=citation.year,
            )
        )
        candidates.extend(
            search_openalex_by_title(
                title=citation.title,
                year=citation.year,
            )
        )

    return select_best_metadata_match(
        citation_title=citation.title,
        citation_authors=citation.authors,
        citation_year=citation.year,
        citation_doi=citation.doi,
        candidates=candidates,
    )


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
        match_result = _find_academic_metadata_match(citation)

        if match_result is not None and match_result.match_status in [
            "ACADEMIC_VERIFIED",
            "ACADEMIC_PARTIAL_MATCH",
        ]:
            record = _build_record_from_academic_match(
                submission_id=submission_id,
                citation=citation,
                match_result=match_result,
            )
        else:
            record = _build_record_from_url_fallback(
                submission_id=submission_id,
                citation=citation,
            )

            if match_result is not None:
                record.raw_response = {
                    **(record.raw_response or {}),
                    "academic_match_attempt": {
                        "match_status": match_result.match_status,
                        "confidence_score": match_result.confidence_score,
                        "provider": match_result.provider,
                        "matched_title": match_result.matched_title,
                        "matched_year": match_result.matched_year,
                        "source_type": match_result.source_type,
                    },
                }

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