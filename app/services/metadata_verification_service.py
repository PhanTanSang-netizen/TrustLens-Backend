from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.enums.metadata_status import MetadataStatus
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
    normalize_doi,
    select_best_metadata_match,
)
from app.processing.metadata.openalex_client import search_openalex_by_title
from app.processing.metadata.url_checker import check_url_exists


@dataclass
class ResolvedCitationMetadata:
    status: MetadataStatus
    provider: str
    confidence_score: float
    query_type: str
    query_value: str | None
    matched_doi: str | None
    matched_title: str | None
    matched_authors: str | None
    matched_year: int | None
    abstract: str | None
    venue: str | None
    publisher: str | None
    source_type: str
    citation_count: int | None
    source_url: str | None
    candidate_count: int
    candidate_margin: float | None
    evidence: dict[str, Any]
    raw_response: dict[str, Any] | None
    provider_error: str | None = None


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
        verification_status=match_result.match_status.value,
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
            "candidate_count": match_result.candidate_count,
            "candidate_margin": match_result.candidate_margin,
            "evidence": match_result.evidence,
            "credibility_explanation": match_result.credibility_explanation,
            "citation_signal": match_result.citation_signal,
            "raw_provider_response": match_result.raw_response,
        },
    )


def _build_record_from_resolved_metadata(
    submission_id: UUID,
    citation: Citation,
    resolved: ResolvedCitationMetadata,
) -> MetadataRecord:
    return MetadataRecord(
        submission_id=submission_id,
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
            "candidate_count": resolved.candidate_count,
            "candidate_margin": resolved.candidate_margin,
            "evidence": resolved.evidence,
            "provider_error": resolved.provider_error,
            "raw_provider_response": resolved.raw_response,
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


def _resolved_from_match(
    citation: Citation,
    match_result: MetadataMatchResult,
) -> ResolvedCitationMetadata:
    raw_response = match_result.raw_response if isinstance(match_result.raw_response, dict) else {}
    abstract = raw_response.get("abstract") or raw_response.get("abstract_inverted_index")

    return ResolvedCitationMetadata(
        status=match_result.match_status,
        provider=match_result.provider,
        confidence_score=match_result.confidence_score,
        query_type="doi" if citation.doi else "title_author_year",
        query_value=normalize_doi(citation.doi) or citation.title,
        matched_doi=normalize_doi(match_result.matched_doi),
        matched_title=match_result.matched_title,
        matched_authors=match_result.matched_authors,
        matched_year=match_result.matched_year,
        abstract=str(abstract) if abstract else None,
        venue=match_result.venue,
        publisher=match_result.publisher,
        source_type=match_result.source_type,
        citation_count=match_result.citation_signal,
        source_url=match_result.source_url,
        candidate_count=match_result.candidate_count,
        candidate_margin=match_result.candidate_margin,
        evidence=match_result.evidence,
        raw_response=match_result.raw_response,
    )


def _resolved_from_url_fallback(citation: Citation) -> ResolvedCitationMetadata:
    if citation.url:
        url_check = check_url_exists(citation.url)
        if url_check.verification_status in {"URL_OK", "URL_WEAK_EVIDENCE", "URL_FORBIDDEN"}:
            status_value = MetadataStatus.URL_ONLY
        elif url_check.verification_status == "URL_UNREACHABLE":
            status_value = MetadataStatus.PROVIDER_UNAVAILABLE
        else:
            status_value = MetadataStatus.NOT_FOUND

        return ResolvedCitationMetadata(
            status=status_value,
            provider="URL_CHECK",
            confidence_score=url_check.confidence_score,
            query_type="url",
            query_value=citation.url,
            matched_doi=None,
            matched_title=citation.title,
            matched_authors=citation.authors,
            matched_year=citation.year,
            abstract=None,
            venue=None,
            publisher=None,
            source_type="website",
            citation_count=None,
            source_url=url_check.final_url,
            candidate_count=0,
            candidate_margin=None,
            evidence={
                "url_status": url_check.verification_status,
                "status_code": url_check.status_code,
                "checked_url": citation.url,
            },
            raw_response={
                "url_status": url_check.verification_status,
                "status_code": url_check.status_code,
                "final_url": url_check.final_url,
                "error": url_check.error,
            },
            provider_error=url_check.error if status_value == MetadataStatus.PROVIDER_UNAVAILABLE else None,
        )

    return ResolvedCitationMetadata(
        status=MetadataStatus.NOT_FOUND,
        provider="BASIC_CHECK",
        confidence_score=0.0,
        query_type="title_year" if citation.title or citation.year else "none",
        query_value=citation.title,
        matched_doi=None,
        matched_title=citation.title,
        matched_authors=citation.authors,
        matched_year=citation.year,
        abstract=None,
        venue=None,
        publisher=None,
        source_type="unknown",
        citation_count=None,
        source_url=None,
        candidate_count=0,
        candidate_margin=None,
        evidence={"reason": "No academic metadata match and no usable URL fallback."},
        raw_response={"reason": "Citation has no DOI or URL metadata provider could verify."},
    )


def verify_citation_metadata(citation: Citation) -> ResolvedCitationMetadata:
    if citation.doi and normalize_doi(citation.doi) is None:
        return ResolvedCitationMetadata(
            status=MetadataStatus.INVALID_IDENTIFIER,
            provider="DOI_VALIDATOR",
            confidence_score=0.0,
            query_type="doi",
            query_value=citation.doi,
            matched_doi=None,
            matched_title=citation.title,
            matched_authors=citation.authors,
            matched_year=citation.year,
            abstract=None,
            venue=None,
            publisher=None,
            source_type="unknown",
            citation_count=None,
            source_url=None,
            candidate_count=0,
            candidate_margin=None,
            evidence={"invalid_doi": citation.doi},
            raw_response={"invalid_doi": citation.doi},
        )

    match_result = _find_academic_metadata_match(citation)

    if match_result is not None and match_result.match_status != MetadataStatus.NOT_FOUND:
        return _resolved_from_match(citation, match_result)

    fallback = _resolved_from_url_fallback(citation)

    if match_result is not None:
        fallback.candidate_count = match_result.candidate_count
        fallback.candidate_margin = match_result.candidate_margin
        fallback.evidence = {
            **fallback.evidence,
            "academic_match_status": match_result.match_status.value,
            "academic_confidence_score": match_result.confidence_score,
            "academic_provider": match_result.provider,
            "academic_evidence": match_result.evidence,
        }
        fallback.raw_response = {
            **(fallback.raw_response or {}),
            "academic_match_attempt": {
                "match_status": match_result.match_status.value,
                "confidence_score": match_result.confidence_score,
                "provider": match_result.provider,
                "matched_title": match_result.matched_title,
                "matched_year": match_result.matched_year,
                "source_type": match_result.source_type,
                "candidate_count": match_result.candidate_count,
                "candidate_margin": match_result.candidate_margin,
                "evidence": match_result.evidence,
            },
        }

    return fallback


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
        resolved = verify_citation_metadata(citation)
        record = _build_record_from_resolved_metadata(
            submission_id=submission_id,
            citation=citation,
            resolved=resolved,
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
