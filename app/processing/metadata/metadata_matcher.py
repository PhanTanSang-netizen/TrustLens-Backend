from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any
import re
import unicodedata
from urllib.parse import urlparse


@dataclass
class MetadataCandidate:
    provider: str
    source_url: str | None
    doi: str | None
    title: str | None
    authors: str | None
    year: int | None
    venue: str | None
    publisher: str | None
    source_type: str
    citation_count: int | None
    raw_response: dict[str, Any] | None


@dataclass
class MetadataMatchResult:
    match_status: str
    confidence_score: float
    provider: str
    source_url: str | None
    matched_title: str | None
    matched_year: int | None
    matched_doi: str | None
    matched_authors: str | None
    venue: str | None
    publisher: str | None
    source_type: str
    credibility_explanation: str
    citation_signal: int | None
    raw_response: dict[str, Any] | None


def normalize_text(text: str | None) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFD", text)
    text = "".join(
        char
        for char in text
        if unicodedata.category(char) != "Mn"
    )
    text = text.lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\b10\.\d{4,9}/\S+\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None

    doi = doi.strip()
    doi = doi.replace("https://doi.org/", "")
    doi = doi.replace("http://doi.org/", "")
    doi = re.sub(r"^doi\s*:\s*", "", doi, flags=re.IGNORECASE)
    doi = doi.strip(" .,\n\t").lower()

    if not re.match(r"^10\.\d{4,9}/\S+$", doi):
        return None

    return doi


def title_similarity(
    input_title: str | None,
    candidate_title: str | None,
) -> float:
    left = normalize_text(input_title)
    right = normalize_text(candidate_title)

    if not left or not right:
        return 0.0

    return SequenceMatcher(None, left, right).ratio()


def year_similarity(
    input_year: int | None,
    candidate_year: int | None,
) -> float:
    if input_year is None or candidate_year is None:
        return 0.0

    diff = abs(int(input_year) - int(candidate_year))

    if diff == 0:
        return 1.0

    if diff == 1:
        return 0.75

    if diff <= 3:
        return 0.45

    return 0.0


def author_similarity(
    input_authors: str | None,
    candidate_authors: str | None,
) -> float:
    left = normalize_text(input_authors)
    right = normalize_text(candidate_authors)

    if not left or not right:
        return 0.0

    return SequenceMatcher(None, left, right).ratio()


def classify_source_type(
    metadata_type: str | None = None,
    venue: str | None = None,
    publisher: str | None = None,
    source_url: str | None = None,
) -> str:
    metadata_type_text = normalize_text(metadata_type)
    venue_text = normalize_text(venue)
    publisher_text = normalize_text(publisher)

    combined = f"{metadata_type_text} {venue_text} {publisher_text}"

    if "journal" in combined or "article journal" in combined:
        return "journal"

    if "conference" in combined or "proceeding" in combined:
        return "conference"

    if "book" in combined or "chapter" in combined:
        return "book"

    if "thesis" in combined or "dissertation" in combined:
        return "thesis"

    if "posted content" in combined or "preprint" in combined:
        return "preprint"

    if source_url:
        domain = urlparse(source_url).netloc.lower()

        if domain:
            if any(
                academic_domain in domain
                for academic_domain in [
                    "doi.org",
                    "crossref.org",
                    "openalex.org",
                    "ieee.org",
                    "acm.org",
                    "springer",
                    "sciencedirect",
                    "tandfonline",
                    "wiley",
                    "sagepub",
                    "mdpi",
                    "frontiersin",
                    "nature",
                    "elsevier",
                    "arxiv.org",
                ]
            ):
                return "academic_web"

            return "website"

    return "unknown"


def build_credibility_explanation(
    source_type: str,
    provider: str,
    confidence_score: float,
) -> str:
    if source_type in ["journal", "conference"]:
        return (
            f"Nguồn được xác minh qua {provider}; loại nguồn {source_type} "
            f"có độ tin cậy học thuật tương đối cao."
        )

    if source_type in ["book", "thesis"]:
        return (
            f"Nguồn được xác minh qua {provider}; loại nguồn {source_type} "
            f"có thể phù hợp tùy ngữ cảnh học thuật."
        )

    if source_type == "preprint":
        return (
            f"Nguồn được xác minh qua {provider}; preprint cần kiểm tra thêm "
            f"vì có thể chưa qua bình duyệt."
        )

    if source_type in ["website", "academic_web"]:
        return (
            f"Nguồn có metadata hoặc URL liên quan nhưng cần kiểm tra thủ công "
            f"thêm; confidence={confidence_score:.2f}."
        )

    return (
        f"Không xác định rõ loại nguồn công bố; cần kiểm tra thủ công. "
        f"confidence={confidence_score:.2f}."
    )


def calculate_candidate_confidence(
    citation_title: str | None,
    citation_authors: str | None,
    citation_year: int | None,
    citation_doi: str | None,
    candidate: MetadataCandidate,
) -> float:
    input_doi = normalize_doi(citation_doi)
    candidate_doi = normalize_doi(candidate.doi)

    if input_doi and candidate_doi and input_doi == candidate_doi:
        return 0.98

    title_score = title_similarity(citation_title, candidate.title)
    year_score = year_similarity(citation_year, candidate.year)
    author_score = author_similarity(citation_authors, candidate.authors)

    confidence = (
        title_score * 0.70
        + year_score * 0.15
        + author_score * 0.15
    )

    return round(min(max(confidence, 0.0), 1.0), 4)


def status_from_confidence(confidence_score: float) -> str:
    if confidence_score >= 0.85:
        return "ACADEMIC_VERIFIED"

    if confidence_score >= 0.60:
        return "ACADEMIC_PARTIAL_MATCH"

    if confidence_score >= 0.45:
        return "ACADEMIC_AMBIGUOUS"

    return "ACADEMIC_NOT_FOUND"


def select_best_metadata_match(
    citation_title: str | None,
    citation_authors: str | None,
    citation_year: int | None,
    citation_doi: str | None,
    candidates: list[MetadataCandidate],
) -> MetadataMatchResult | None:
    if not candidates:
        return None

    ranked: list[tuple[float, MetadataCandidate]] = []

    for candidate in candidates:
        confidence = calculate_candidate_confidence(
            citation_title=citation_title,
            citation_authors=citation_authors,
            citation_year=citation_year,
            citation_doi=citation_doi,
            candidate=candidate,
        )
        ranked.append((confidence, candidate))

    ranked.sort(key=lambda item: item[0], reverse=True)

    best_confidence, best_candidate = ranked[0]

    source_type = classify_source_type(
        metadata_type=best_candidate.source_type,
        venue=best_candidate.venue,
        publisher=best_candidate.publisher,
        source_url=best_candidate.source_url,
    )

    return MetadataMatchResult(
        match_status=status_from_confidence(best_confidence),
        confidence_score=best_confidence,
        provider=best_candidate.provider,
        source_url=best_candidate.source_url,
        matched_title=best_candidate.title,
        matched_year=best_candidate.year,
        matched_doi=best_candidate.doi,
        matched_authors=best_candidate.authors,
        venue=best_candidate.venue,
        publisher=best_candidate.publisher,
        source_type=source_type,
        credibility_explanation=build_credibility_explanation(
            source_type=source_type,
            provider=best_candidate.provider,
            confidence_score=best_confidence,
        ),
        citation_signal=best_candidate.citation_count,
        raw_response=best_candidate.raw_response,
    )