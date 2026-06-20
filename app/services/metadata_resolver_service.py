from __future__ import annotations

from dataclasses import dataclass

from app.models.citation import Citation
from app.services.metadata_verification_service import verify_citation_metadata


@dataclass
class ResolvedMetadata:
    provider: str
    query_type: str
    query_value: str | None
    source_url: str | None
    matched_title: str | None
    matched_year: int | None
    verification_status: str
    confidence_score: float
    raw_response: dict


def resolve_citation_metadata(citation: Citation) -> ResolvedMetadata:
    resolved = verify_citation_metadata(citation)

    return ResolvedMetadata(
        provider=resolved.provider,
        query_type=resolved.query_type,
        query_value=resolved.query_value,
        source_url=resolved.source_url,
        matched_title=resolved.matched_title,
        matched_year=resolved.matched_year,
        verification_status=resolved.status.value,
        confidence_score=resolved.confidence_score,
        raw_response={
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
