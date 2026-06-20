from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any
import re
import unicodedata
from urllib.parse import urlparse

from app.core.enums.metadata_status import MetadataStatus


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
    match_status: MetadataStatus
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
    candidate_count: int
    candidate_margin: float | None
    evidence: dict[str, Any]
    raw_response: dict[str, Any] | None


VIETNAMESE_STOPWORDS = {
    "va",
    "cua",
    "cho",
    "theo",
    "trong",
    "ve",
    "la",
    "cac",
    "nhung",
    "mot",
    "tu",
    "tai",
    "tap",
    "lan",
    "thu",
    "nay",
    "hien",
    "qua",
    "voi",
    "den",
    "duoc",
    "nham",
    "tren",
    "duoi",
    "sau",
    "truoc",
}

ENGLISH_STOPWORDS = {
    "and",
    "or",
    "of",
    "the",
    "a",
    "an",
    "in",
    "on",
    "for",
    "to",
    "with",
    "by",
    "from",
}

STOPWORDS = VIETNAMESE_STOPWORDS | ENGLISH_STOPWORDS


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
    doi = doi.replace("https://dx.doi.org/", "")
    doi = doi.replace("http://dx.doi.org/", "")
    doi = re.sub(r"^doi\s*:\s*", "", doi, flags=re.IGNORECASE)
    doi = doi.strip(" .,\n\t").lower()

    if not re.match(r"^10\.\d{4,9}/\S+$", doi):
        return None

    return doi


def tokenize_text(text: str | None) -> list[str]:
    normalized = normalize_text(text)

    if not normalized:
        return []

    return [
        token
        for token in normalized.split()
        if len(token) >= 2 and token not in STOPWORDS
    ]


def is_title_too_short_for_academic_search(title: str | None) -> bool:
    tokens = tokenize_text(title)

    if len(tokens) < 4:
        return True

    normalized = normalize_text(title)

    if len(normalized) < 18:
        return True

    return False


def token_overlap_scores(
    input_text: str | None,
    candidate_text: str | None,
) -> tuple[float, float, float, float]:
    input_tokens = tokenize_text(input_text)
    candidate_tokens = tokenize_text(candidate_text)

    if not input_tokens or not candidate_tokens:
        return 0.0, 0.0, 0.0, 0.0

    input_set = set(input_tokens)
    candidate_set = set(candidate_tokens)

    intersection = input_set & candidate_set
    union = input_set | candidate_set

    jaccard = len(intersection) / len(union) if union else 0.0
    input_coverage = len(intersection) / len(input_set) if input_set else 0.0
    candidate_coverage = len(intersection) / len(candidate_set) if candidate_set else 0.0

    length_ratio = min(len(input_tokens), len(candidate_tokens)) / max(
        len(input_tokens),
        len(candidate_tokens),
    )

    return jaccard, input_coverage, candidate_coverage, length_ratio


def title_similarity(
    input_title: str | None,
    candidate_title: str | None,
) -> float:
    left = normalize_text(input_title)
    right = normalize_text(candidate_title)

    if not left or not right:
        return 0.0

    sequence_ratio = SequenceMatcher(None, left, right).ratio()
    jaccard, input_coverage, candidate_coverage, length_ratio = token_overlap_scores(
        input_title,
        candidate_title,
    )

    score = (
        sequence_ratio * 0.40
        + jaccard * 0.30
        + input_coverage * 0.20
        + candidate_coverage * 0.10
    )

    # Nếu title chỉ trùng vài từ khóa rời rạc thì không được đẩy lên partial match.
    if jaccard < 0.30:
        score = min(score, 0.50)

    if input_coverage < 0.45 and jaccard < 0.45:
        score = min(score, 0.58)

    # Nếu độ dài hai title quá lệch, giảm độ tin cậy.
    if length_ratio < 0.55:
        score = min(score, 0.62)

    # Title ngắn như "trồng người" quá mơ hồ, không đủ để xác minh học thuật tự động.
    if is_title_too_short_for_academic_search(input_title):
        score = min(score, 0.62)

    return round(min(max(score, 0.0), 1.0), 4)


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
        return 0.65

    if diff <= 3:
        return 0.35

    return 0.0


def author_similarity(
    input_authors: str | None,
    candidate_authors: str | None,
) -> float:
    left = normalize_text(input_authors)
    right = normalize_text(candidate_authors)

    if not left or not right:
        return 0.0

    sequence_ratio = SequenceMatcher(None, left, right).ratio()
    jaccard, input_coverage, candidate_coverage, _ = token_overlap_scores(
        input_authors,
        candidate_authors,
    )

    score = (
        sequence_ratio * 0.40
        + jaccard * 0.30
        + input_coverage * 0.15
        + candidate_coverage * 0.15
    )

    return round(min(max(score, 0.0), 1.0), 4)


def has_author_conflict(
    input_authors: str | None,
    candidate_authors: str | None,
) -> bool:
    if not input_authors or not candidate_authors:
        return False

    score = author_similarity(input_authors, candidate_authors)

    return score < 0.20


def has_year_conflict(
    input_year: int | None,
    candidate_year: int | None,
) -> bool:
    if input_year is None or candidate_year is None:
        return False

    return abs(int(input_year) - int(candidate_year)) > 3


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

    if "journal" in combined or "journal article" in combined or "article" in combined:
        return "journal"

    if "conference" in combined or "proceeding" in combined:
        return "conference"

    if "book" in combined or "chapter" in combined:
        return "book"

    if "thesis" in combined or "dissertation" in combined:
        return "thesis"

    if "posted content" in combined or "posted" in combined or "preprint" in combined:
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
            f"Nguồn có metadata hoặc URL liên quan nhưng cần kiểm tra thủ công thêm; "
            f"confidence={confidence_score:.2f}."
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

    # DOI exact match là bằng chứng mạnh nhất.
    if input_doi and candidate_doi and input_doi == candidate_doi:
        return 0.98

    # Nếu citation có DOI nhưng candidate trả DOI khác, không được xem là match.
    if input_doi and candidate_doi and input_doi != candidate_doi:
        return 0.0

    title_score = title_similarity(citation_title, candidate.title)
    year_score = year_similarity(citation_year, candidate.year)
    author_score = author_similarity(citation_authors, candidate.authors)

    confidence = (
        title_score * 0.75
        + year_score * 0.15
        + author_score * 0.10
    )

    if has_year_conflict(citation_year, candidate.year):
        confidence -= 0.25

    if has_author_conflict(citation_authors, candidate.authors) and title_score < 0.90:
        confidence -= 0.20

    # Không cho title yếu vượt lên thành ambiguous/partial chỉ nhờ year trùng.
    if title_score < 0.65:
        confidence = min(confidence, 0.44)

    if title_score < 0.78:
        confidence = min(confidence, 0.64)

    if title_score < 0.90:
        confidence = min(confidence, 0.77)

    # Nếu có cả hai năm nhưng không gần nhau, không được partial.
    if citation_year is not None and candidate.year is not None and year_score == 0.0:
        confidence = min(confidence, 0.64)

    return round(min(max(confidence, 0.0), 1.0), 4)


def status_from_confidence(
    confidence_score: float,
    candidate_margin: float | None = None,
    doi_exact_match: bool = False,
) -> MetadataStatus:
    if doi_exact_match:
        return MetadataStatus.VERIFIED

    if confidence_score >= 0.90:
        if candidate_margin is not None and candidate_margin < 0.05:
            return MetadataStatus.AMBIGUOUS
        return MetadataStatus.VERIFIED

    if confidence_score >= 0.78:
        return MetadataStatus.PARTIAL_MATCH

    if confidence_score >= 0.65:
        return MetadataStatus.AMBIGUOUS

    return MetadataStatus.NOT_FOUND


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
    second_confidence = ranked[1][0] if len(ranked) > 1 else None
    candidate_margin = (
        round(best_confidence - second_confidence, 4)
        if second_confidence is not None
        else None
    )
    doi_exact_match = bool(
        normalize_doi(citation_doi)
        and normalize_doi(best_candidate.doi)
        and normalize_doi(citation_doi) == normalize_doi(best_candidate.doi)
    )

    source_type = classify_source_type(
        metadata_type=best_candidate.source_type,
        venue=best_candidate.venue,
        publisher=best_candidate.publisher,
        source_url=best_candidate.source_url,
    )

    return MetadataMatchResult(
        match_status=status_from_confidence(
            best_confidence,
            candidate_margin=candidate_margin,
            doi_exact_match=doi_exact_match,
        ),
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
        candidate_count=len(ranked),
        candidate_margin=candidate_margin,
        evidence={
            "title_similarity": title_similarity(citation_title, best_candidate.title),
            "author_similarity": author_similarity(citation_authors, best_candidate.authors),
            "year_similarity": year_similarity(citation_year, best_candidate.year),
            "doi_exact_match": doi_exact_match,
            "candidate_count": len(ranked),
            "candidate_margin": candidate_margin,
            "provider": best_candidate.provider,
            "second_best_confidence": second_confidence,
        },
        raw_response=best_candidate.raw_response,
    )
