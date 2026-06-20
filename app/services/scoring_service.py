from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from math import sqrt
import re
from typing import Any
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.enums.metadata_status import MetadataStatus, normalize_metadata_status
from app.core.trust_score_definition import DEFAULT_THRESHOLDS, DEFAULT_WEIGHTS, SCORING_VERSION
from app.models.citation import Citation
from app.models.metadata_record import MetadataRecord
from app.models.scoring_config import ScoringConfig
from app.models.trust_score import CitationScore
from app.models.warning import Warning


@dataclass
class ComponentScore:
    score: float
    max_score: float
    reason: str
    evidence: dict[str, Any]
    confidence: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 2),
            "max_score": self.max_score,
            "reason": self.reason,
            "evidence": self.evidence,
            "confidence": round(self.confidence, 3),
        }


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _warning(
    code: str,
    severity: str,
    message: str,
    recommendation: str,
    evidence: dict | None = None,
) -> dict:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "recommendation": recommendation,
        "evidence": evidence or {},
    }


def _deep_merge(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(base)
    if not isinstance(override, dict):
        return merged
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_scoring_config(scoring_config: ScoringConfig | None) -> tuple[str, dict[str, int], dict[str, Any]]:
    weights = _deep_merge(DEFAULT_WEIGHTS, scoring_config.weights_json if scoring_config else None)
    thresholds = _deep_merge(DEFAULT_THRESHOLDS, scoring_config.thresholds_json if scoring_config else None)

    allowed_weight_keys = set(DEFAULT_WEIGHTS)
    weights = {key: int(value) for key, value in weights.items() if key in allowed_weight_keys}

    if set(weights) != allowed_weight_keys or sum(weights.values()) != 100 or any(value < 0 for value in weights.values()):
        weights = dict(DEFAULT_WEIGHTS)

    version = SCORING_VERSION
    if scoring_config is not None:
        version = f"{scoring_config.name}-v{scoring_config.version}"

    return version, weights, thresholds


def _metadata_raw(metadata: MetadataRecord | None) -> dict[str, Any]:
    return metadata.raw_response if metadata is not None and isinstance(metadata.raw_response, dict) else {}


def _metadata_status(metadata: MetadataRecord | None) -> MetadataStatus:
    return normalize_metadata_status(metadata.verification_status if metadata is not None else None)


def _source_type(metadata: MetadataRecord | None, citation: Citation) -> str:
    raw = _metadata_raw(metadata)
    raw_type = raw.get("source_type") or raw.get("type")
    source_type = str(raw_type).lower() if raw_type else ""

    aliases = {
        "journal-article": "journal",
        "proceedings-article": "conference",
        "book-chapter": "book",
        "posted-content": "preprint",
        "academic_web": "journal",
    }
    if source_type in aliases:
        return aliases[source_type]
    if source_type:
        return source_type

    url = (citation.url or "").lower()
    if any(domain in url for domain in ["medium.com", "wordpress", "blogspot"]):
        return "blog"
    if url:
        return "website"
    return "unknown"


def _text_tokens(text: str | None) -> list[str]:
    if not text:
        return []
    return [
        token
        for token in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(token) > 3
    ]


def _token_overlap(left: str | None, right: str | None) -> float:
    left_tokens = set(_text_tokens(left))
    right_tokens = set(_text_tokens(right))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _cosine_token_similarity(left: str | None, right: str | None) -> float:
    left_counts = Counter(_text_tokens(left))
    right_counts = Counter(_text_tokens(right))
    if not left_counts or not right_counts:
        return 0.0

    dot = sum(left_counts[token] * right_counts.get(token, 0) for token in left_counts)
    left_norm = sqrt(sum(value * value for value in left_counts.values()))
    right_norm = sqrt(sum(value * value for value in right_counts.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _reference_text(citation: Citation, metadata: MetadataRecord | None) -> tuple[str, bool]:
    raw = _metadata_raw(metadata)
    abstract = raw.get("abstract")
    if isinstance(abstract, dict):
        abstract = " ".join(str(key) for key in abstract.keys())

    parts = [
        metadata.matched_title if metadata is not None else None,
        citation.title,
        str(abstract) if abstract else None,
        raw.get("venue"),
        raw.get("publisher"),
    ]
    text = " ".join(part for part in parts if part)
    return text or citation.raw_text, bool(abstract)


def _label_from_score(score: float, thresholds: dict[str, Any]) -> str:
    labels = thresholds.get("labels", DEFAULT_THRESHOLDS["labels"])
    if score >= labels.get("reliable", 85):
        return "reliable"
    if score >= labels.get("acceptable", 70):
        return "acceptable"
    if score >= labels.get("needs_review", 50):
        return "needs_review"
    return "high_risk"


def _apply_label_cap(label: str, cap: str | None) -> str:
    if cap is None:
        return label
    order = ["high_risk", "needs_review", "acceptable", "reliable"]
    return order[min(order.index(label), order.index(cap))]


def _score_completeness(citation: Citation, metadata: MetadataRecord | None, source_type: str) -> ComponentScore:
    raw = _metadata_raw(metadata)
    venue = raw.get("venue")
    publisher = raw.get("publisher")
    matched_doi = raw.get("matched_doi")

    if source_type in {"journal", "conference", "preprint"}:
        checks = {
            "authors": (bool(citation.authors or raw.get("matched_authors")), 2),
            "title": (bool(citation.title or (metadata.matched_title if metadata else None)), 2),
            "year": (bool(citation.year or (metadata.matched_year if metadata else None)), 1),
            "venue": (bool(venue), 2),
            "doi_or_url": (bool(citation.doi or citation.url or matched_doi), 2),
            "publisher": (bool(publisher), 1),
        }
    elif source_type == "book":
        checks = {
            "authors_or_editors": (bool(citation.authors or raw.get("matched_authors")), 2),
            "title": (bool(citation.title or (metadata.matched_title if metadata else None)), 2),
            "year": (bool(citation.year or (metadata.matched_year if metadata else None)), 1),
            "publisher": (bool(publisher), 2),
            "isbn_or_url": (bool(citation.url or raw.get("isbn")), 2),
            "edition": (bool(raw.get("edition")), 1),
        }
    elif source_type in {"website", "blog"}:
        checks = {
            "author_or_organization": (bool(citation.authors or publisher), 2),
            "page_title": (bool(citation.title or (metadata.matched_title if metadata else None)), 2),
            "publication_date": (bool(citation.year or (metadata.matched_year if metadata else None)), 2),
            "domain_or_site": (bool(venue or publisher or citation.url), 2),
            "url": (bool(citation.url or (metadata.source_url if metadata else None)), 2),
        }
    else:
        checks = {
            "authors": (bool(citation.authors), 2.5),
            "title": (bool(citation.title), 2.5),
            "year": (citation.year is not None, 2.5),
            "doi_or_url": (bool(citation.doi or citation.url), 2.5),
        }

    score = sum(points for present, points in checks.values() if present)
    missing = [field for field, (present, _) in checks.items() if not present]
    return ComponentScore(
        score=round(score, 2),
        max_score=10,
        reason="Metadata fields are sufficiently complete." if not missing else "Citation is missing metadata fields.",
        evidence={"source_type": source_type, "missing_fields": missing},
        confidence=0.9 if not missing else 0.65,
    )


def _score_verification(metadata: MetadataRecord | None) -> ComponentScore:
    status_value = _metadata_status(metadata)
    status_scores = {
        MetadataStatus.VERIFIED: 25,
        MetadataStatus.PARTIAL_MATCH: 18,
        MetadataStatus.AMBIGUOUS: 10,
        MetadataStatus.URL_ONLY: 7,
        MetadataStatus.NOT_FOUND: 3,
        MetadataStatus.PROVIDER_UNAVAILABLE: 8,
        MetadataStatus.INVALID_IDENTIFIER: 0,
    }
    raw = _metadata_raw(metadata)
    evidence = {
        "status": status_value.value,
        "matched_doi": raw.get("matched_doi"),
        "title_similarity": raw.get("evidence", {}).get("title_similarity") if isinstance(raw.get("evidence"), dict) else None,
        "author_similarity": raw.get("evidence", {}).get("author_similarity") if isinstance(raw.get("evidence"), dict) else None,
        "year_similarity": raw.get("evidence", {}).get("year_similarity") if isinstance(raw.get("evidence"), dict) else None,
        "candidate_count": raw.get("candidate_count", 0),
        "candidate_margin": raw.get("candidate_margin"),
        "provider": metadata.provider if metadata is not None else "unknown",
    }
    return ComponentScore(
        score=status_scores[status_value],
        max_score=25,
        reason=f"Metadata verification status is {status_value.value}.",
        evidence=evidence,
        confidence=float(metadata.confidence_score if metadata is not None else 0.0),
    )


def _score_credibility(
    metadata: MetadataRecord | None,
    source_type: str,
    thresholds: dict[str, Any],
) -> ComponentScore:
    raw = _metadata_raw(metadata)
    publisher = raw.get("publisher")
    venue = raw.get("venue")
    status_value = _metadata_status(metadata)
    source_type_scores = {
        "journal": 8,
        "conference": 7,
        "book": 7,
        "thesis": 6,
        "preprint": 5,
        "standard": 7,
        "technical_documentation": 6,
        "institutional_website": 5,
        "website": 3,
        "blog": 1,
        "unknown": 2,
    }

    publisher_score = 0
    publisher_whitelist = [str(item).lower() for item in thresholds.get("publisher_whitelist", [])]
    if publisher and status_value in {MetadataStatus.VERIFIED, MetadataStatus.PARTIAL_MATCH}:
        publisher_score = 3
        if any(item in str(publisher).lower() for item in publisher_whitelist):
            publisher_score += 2

    venue_score = 0
    venue_whitelist = [str(item).lower() for item in thresholds.get("venue_whitelist", [])]
    if venue and status_value in {MetadataStatus.VERIFIED, MetadataStatus.PARTIAL_MATCH}:
        venue_score = 2
        if any(item in str(venue).lower() for item in venue_whitelist):
            venue_score += 2

    publication_status = str(raw.get("publication_status") or "").lower()
    if "retract" in publication_status or raw.get("is_retracted") is True:
        publication_status_score = 0
    elif raw.get("publication_status") or raw.get("publication_status_verified"):
        publication_status_score = 3
    else:
        publication_status_score = 1

    source_score = source_type_scores.get(source_type, 2)
    score = min(20, source_score + publisher_score + venue_score + publication_status_score)
    return ComponentScore(
        score=round(score, 2),
        max_score=20,
        reason="Source credibility is based on type, publisher, venue and publication-status evidence.",
        evidence={
            "source_type": source_type,
            "source_type_score": source_score,
            "publisher": publisher,
            "publisher_score": publisher_score,
            "venue": venue,
            "venue_score": venue_score,
            "publication_status_score": publication_status_score,
        },
        confidence=0.75 if status_value in {MetadataStatus.VERIFIED, MetadataStatus.PARTIAL_MATCH} else 0.45,
    )


def _score_relevance(
    citation: Citation,
    metadata: MetadataRecord | None,
    report_text: str,
    thresholds: dict[str, Any],
) -> ComponentScore:
    reference_text, has_abstract = _reference_text(citation, metadata)
    semantic_similarity = _cosine_token_similarity(report_text, reference_text)
    lexical_similarity = _token_overlap(report_text, reference_text)
    raw_relevance = semantic_similarity * 0.70 + lexical_similarity * 0.30
    relevance_thresholds = thresholds.get("relevance", DEFAULT_THRESHOLDS["relevance"])

    if raw_relevance >= relevance_thresholds.get("high", 0.80):
        score = 20
    elif raw_relevance >= relevance_thresholds.get("good", 0.70):
        score = 17
    elif raw_relevance >= relevance_thresholds.get("medium", 0.60):
        score = 14
    elif raw_relevance >= relevance_thresholds.get("weak", 0.50):
        score = 10
    elif raw_relevance >= relevance_thresholds.get("low", 0.40):
        score = 7
    else:
        score = 3

    return ComponentScore(
        score=score,
        max_score=20,
        reason="Relevance uses token cosine similarity plus lexical overlap.",
        evidence={
            "raw_relevance": round(raw_relevance, 4),
            "semantic_similarity": round(semantic_similarity, 4),
            "lexical_similarity": round(lexical_similarity, 4),
            "model": "lexical-tfidf-fallback",
            "has_abstract": has_abstract,
        },
        confidence=0.75 if has_abstract else 0.5,
    )


def _score_recency(
    citation: Citation,
    metadata: MetadataRecord | None,
    thresholds: dict[str, Any],
) -> ComponentScore:
    recency = thresholds.get("recency", DEFAULT_THRESHOLDS["recency"])
    current_year = datetime.now(timezone.utc).year
    matched_year = metadata.matched_year if metadata is not None else None
    year = matched_year or citation.year

    if year is None:
        return ComponentScore(
            score=4,
            max_score=10,
            reason="Publication year is unknown.",
            evidence={"year": None, "year_source": "unknown"},
            confidence=0.35,
        )

    age = max(0, current_year - int(year))
    if age <= recency.get("fresh_years", 3):
        score = 10
    elif age <= recency.get("acceptable_years", 5):
        score = 8
    elif age <= recency.get("review_years", 10):
        score = 6
    elif age <= recency.get("old_years", 15):
        score = 4
    else:
        score = 2

    return ComponentScore(
        score=score,
        max_score=10,
        reason="Recency uses matched metadata year before parsed citation year.",
        evidence={
            "year": year,
            "year_source": "matched_year" if matched_year else "parsed_year",
            "parsed_year": citation.year,
            "matched_year": matched_year,
            "age": age,
        },
        confidence=0.85 if matched_year else 0.65,
    )


def _style_family(detected_style: str | None) -> str:
    style = (detected_style or "UNKNOWN").upper()
    if style in {"APA7", "APA", "AUTHOR_YEAR"}:
        return "APA7"
    if style in {"IEEE", "NUMBERED"}:
        return "IEEE"
    if style == "MLA":
        return "MLA"
    if style == "ACM":
        return "ACM"
    return "UNKNOWN"


def _score_style(citation: Citation, expected_style: str | None) -> ComponentScore:
    detected = _style_family(citation.detected_style)
    expected = _style_family(expected_style) if expected_style else None
    if expected and detected != "UNKNOWN" and detected != expected:
        score = 6
        reason = "Citation style differs from the assignment requirement."
    elif detected == "UNKNOWN":
        score = 5
        reason = "Citation style could not be identified confidently."
    else:
        score = 10
        reason = "Citation style matches or no required style was configured."

    return ComponentScore(
        score=score,
        max_score=10,
        reason=reason,
        evidence={"expected_style": expected, "detected_style": detected, "raw_detected_style": citation.detected_style},
        confidence=0.85 if detected != "UNKNOWN" else 0.45,
    )


def _score_duplicate(
    citation: Citation,
    source_type: str,
    duplicate_of: UUID | None,
    source_count: int,
    total_citations: int,
) -> ComponentScore:
    concentration_limit = max(1, total_citations // 2)
    if duplicate_of is not None:
        score = 1
        reason = "Duplicate reference detected."
    elif source_count > concentration_limit and total_citations >= 3:
        score = 3
        reason = "References are concentrated in one source type."
    else:
        score = 5
        reason = "No duplicate or concentration risk detected."

    return ComponentScore(
        score=score,
        max_score=5,
        reason=reason,
        evidence={
            "duplicate_of": str(duplicate_of) if duplicate_of else None,
            "source_type": source_type,
            "source_type_count": source_count,
            "total_citations": total_citations,
        },
        confidence=0.9,
    )


def _apply_component_weights(
    components: dict[str, ComponentScore],
    weights: dict[str, int],
) -> dict[str, ComponentScore]:
    weight_keys = {
        "c1": "c1_completeness",
        "c2": "c2_verification",
        "c3": "c3_credibility",
        "c4": "c4_relevance",
        "c5": "c5_recency",
        "c6": "c6_style",
        "c7": "c7_duplicate_concentration",
    }
    weighted: dict[str, ComponentScore] = {}
    for component_key, component in components.items():
        target_max = float(weights[weight_keys[component_key]])
        if component.max_score <= 0:
            scaled_score = 0.0
        else:
            scaled_score = component.score / component.max_score * target_max
        weighted[component_key] = ComponentScore(
            score=round(scaled_score, 2),
            max_score=target_max,
            reason=component.reason,
            evidence={**component.evidence, "configured_weight": target_max},
            confidence=component.confidence,
        )
    return weighted


def _evaluate_penalties(
    citation: Citation,
    metadata: MetadataRecord | None,
    components: dict[str, ComponentScore],
    duplicate_of: UUID | None,
) -> list[dict[str, Any]]:
    status_value = _metadata_status(metadata)
    raw = _metadata_raw(metadata)
    penalties: list[dict[str, Any]] = []

    if status_value == MetadataStatus.INVALID_IDENTIFIER:
        penalties.append({"code": "INVALID_IDENTIFIER", "value": 10, "label_cap": "high_risk", "evidence": {"doi": citation.doi}})

    evidence = raw.get("evidence") if isinstance(raw.get("evidence"), dict) else {}
    if citation.doi and evidence.get("doi_exact_match") is False and raw.get("matched_doi"):
        penalties.append({"code": "DOI_CONFLICT", "value": 15, "label_cap": "high_risk", "evidence": {"citation_doi": citation.doi, "matched_doi": raw.get("matched_doi")}})

    if duplicate_of is not None:
        penalties.append({"code": "DUPLICATE_REFERENCE", "value": 5, "label_cap": "needs_review", "evidence": {"duplicate_of": str(duplicate_of)}})

    if "retract" in str(raw.get("publication_status") or "").lower() or raw.get("is_retracted") is True:
        penalties.append({"code": "RETRACTED_SOURCE", "value": 30, "label_cap": "high_risk", "evidence": {"publication_status": raw.get("publication_status")}})

    if components["c4"].score <= 3:
        penalties.append({"code": "LOW_RELEVANCE", "value": 3, "label_cap": "needs_review", "evidence": components["c4"].evidence})

    return penalties


def _warnings_for_reference(
    citation: Citation,
    metadata: MetadataRecord | None,
    components: dict[str, ComponentScore],
    penalties: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    status_value = _metadata_status(metadata)

    missing = components["c1"].evidence.get("missing_fields", [])
    if missing:
        warnings.append(_warning("MISSING_REQUIRED_FIELD", "medium", "Citation is missing important metadata fields.", "Add or correct the missing citation fields.", {"missing_fields": missing}))

    if status_value == MetadataStatus.NOT_FOUND:
        warnings.append(_warning("SOURCE_NOT_FOUND", "high", "No metadata match was found. This is not proof that the source is fake.", "Check DOI/title manually or replace the source.", components["c2"].evidence))
    elif status_value == MetadataStatus.PROVIDER_UNAVAILABLE:
        warnings.append(_warning("PROVIDER_UNAVAILABLE", "medium", "Metadata provider was unavailable or inconclusive.", "Retry later or verify manually.", components["c2"].evidence))
    elif status_value == MetadataStatus.URL_ONLY:
        warnings.append(_warning("URL_ONLY", "medium", "Only the URL could be checked; academic metadata was not verified.", "Prefer sources with DOI or verifiable academic metadata.", components["c2"].evidence))
    elif status_value == MetadataStatus.INVALID_IDENTIFIER:
        warnings.append(_warning("INVALID_IDENTIFIER", "high", "Citation has an invalid identifier.", "Correct the DOI or remove the invalid identifier.", {"doi": citation.doi}))

    if components["c3"].score <= 8:
        warnings.append(_warning("LOW_CREDIBILITY_SOURCE", "medium", "Source has limited credibility evidence.", "Prefer academic, institutional, or well documented sources.", components["c3"].evidence))

    if components["c4"].score <= 7:
        warnings.append(_warning("LOW_RELEVANCE", "medium", "Citation appears weakly related to the report context.", "Check whether this source supports the report topic.", components["c4"].evidence))

    if components["c5"].evidence.get("age", 0) and components["c5"].evidence["age"] > 10:
        warnings.append(_warning("OUTDATED_REFERENCE", "medium", "Reference is older than the default recency window.", "Use a newer source unless this is foundational.", components["c5"].evidence))

    if citation.year and metadata is not None and metadata.matched_year and citation.year != metadata.matched_year:
        warnings.append(_warning("YEAR_CONFLICT", "medium", "Parsed year differs from matched metadata year.", "Review the citation year.", {"parsed_year": citation.year, "matched_year": metadata.matched_year}))

    if components["c6"].score < 10:
        warnings.append(_warning("STYLE_REVIEW", "low", components["c6"].reason, "Normalize citation style for the assignment.", components["c6"].evidence))

    for penalty in penalties:
        warnings.append(_warning(penalty["code"], "high", f"Penalty applied: {penalty['code']}.", "Review this citation manually.", penalty.get("evidence", {})))

    return warnings


def _report_text_from_context(document_text: str | None, report_context: dict[str, Any] | None) -> str:
    if isinstance(report_context, dict):
        for key in ["scoring_text", "report_text", "body_text"]:
            if report_context.get(key):
                return str(report_context[key])
    return document_text or ""


def score_submission(
    db: Session,
    submission_id: UUID,
    citations: list[Citation],
    metadata_records: list[MetadataRecord],
    document_text: str | None = None,
    expected_style: str | None = None,
    scoring_config: ScoringConfig | None = None,
    report_context: dict[str, Any] | None = None,
) -> dict:
    config_version, weights, thresholds = _load_scoring_config(scoring_config)
    report_text = _report_text_from_context(document_text, report_context)

    if citations:
        db.execute(delete(CitationScore).where(CitationScore.citation_id.in_([citation.id for citation in citations])))
    db.execute(delete(Warning).where(Warning.submission_id == submission_id))

    metadata_by_citation = {record.citation_id: record for record in metadata_records}
    duplicate_keys: dict[str, UUID] = {}
    source_types = {
        citation.id: _source_type(metadata_by_citation.get(citation.id), citation)
        for citation in citations
    }
    source_counter = Counter(source_types.values())

    citation_payloads = []
    all_warnings = []
    totals = Counter()
    final_scores: list[float] = []
    confidence_scores: list[float] = []
    unresolved_count = 0

    for citation in citations:
        metadata = metadata_by_citation.get(citation.id)
        source_type = source_types[citation.id]
        key = (citation.doi or citation.url or citation.title or "").strip().lower()
        duplicate_of = duplicate_keys.get(key) if key else None
        if key and duplicate_of is None:
            duplicate_keys[key] = citation.id

        components = {
            "c1": _score_completeness(citation, metadata, source_type),
            "c2": _score_verification(metadata),
            "c3": _score_credibility(metadata, source_type, thresholds),
            "c4": _score_relevance(citation, metadata, report_text, thresholds),
            "c5": _score_recency(citation, metadata, thresholds),
            "c6": _score_style(citation, expected_style),
            "c7": _score_duplicate(citation, source_type, duplicate_of, source_counter[source_type], len(citations)),
        }
        components = _apply_component_weights(components, weights)

        penalties = _evaluate_penalties(citation, metadata, components, duplicate_of)
        penalty_total = sum(float(item["value"]) for item in penalties)
        base_score = sum(component.score for component in components.values())
        final_score = round(_clamp(base_score - penalty_total, 0, 100), 2)
        confidence_score = round(_clamp(sum(component.confidence for component in components.values()) / len(components), 0, 1), 3)
        label = _label_from_score(final_score, thresholds)
        for penalty in penalties:
            label = _apply_label_cap(label, penalty.get("label_cap"))

        warnings = _warnings_for_reference(citation, metadata, components, penalties)
        for warning in warnings:
            db.add(Warning(submission_id=submission_id, citation_id=citation.id, code=warning["code"], severity=warning["severity"], message=warning["message"], recommendation=warning["recommendation"], evidence=warning["evidence"]))

        explanations = {key_name: component.as_dict() for key_name, component in components.items()}
        explanations["penalties"] = penalties
        explanations["base_score"] = round(base_score, 2)
        explanations["penalty_total"] = round(penalty_total, 2)
        explanations["final_label"] = label

        db.add(
            CitationScore(
                citation_id=citation.id,
                scoring_config_version=config_version,
                c1=components["c1"].score,
                c2=components["c2"].score,
                c3=components["c3"].score,
                c4=components["c4"].score,
                c5=components["c5"].score,
                c6=components["c6"].score,
                c7=components["c7"].score,
                c8=0,
                reference_trust_score=final_score,
                confidence_score=confidence_score,
                explanations=explanations,
            )
        )

        raw_metadata = _metadata_raw(metadata)
        status_value = _metadata_status(metadata)
        if status_value in {MetadataStatus.NOT_FOUND, MetadataStatus.PROVIDER_UNAVAILABLE, MetadataStatus.INVALID_IDENTIFIER}:
            unresolved_count += 1

        citation_payloads.append({
            "citation_id": str(citation.id),
            "raw_text": citation.raw_text,
            "normalized_fields": {
                "title": citation.title,
                "authors": citation.authors,
                "year": citation.year,
                "doi": citation.doi,
                "url": citation.url,
                "venue": raw_metadata.get("venue"),
            },
            "metadata": {
                "status": status_value.value,
                "provider": metadata.provider if metadata is not None else "unknown",
                "confidence": metadata.confidence_score if metadata is not None else 0.0,
                "candidate_count": raw_metadata.get("candidate_count", 0),
                "candidate_margin": raw_metadata.get("candidate_margin"),
                "source_type": source_type,
                "evidence": raw_metadata.get("evidence", {}),
            },
            "components": explanations,
            "penalties": penalties,
            "base_score": round(base_score, 2),
            "final_score": final_score,
            "confidence_score": confidence_score,
            "final_label": label,
            "warnings": warnings,
        })

        all_warnings.extend(warnings)
        final_scores.append(final_score)
        confidence_scores.append(confidence_score)
        for key_name, component in components.items():
            totals[key_name] += component.score

    count = max(1, len(citations))
    mean_score = sum(final_scores) / count if final_scores else 0.0
    min_score = min(final_scores) if final_scores else 0.0
    report_score = round(mean_score if len(final_scores) <= 1 else (mean_score * 0.70 + min_score * 0.30), 2)

    report_penalties = []
    unresolved_ratio = unresolved_count / count
    if unresolved_ratio > 0.30:
        report_penalties.append({"code": "HIGH_UNRESOLVED_METADATA_RATIO", "value": 5, "evidence": {"unresolved_ratio": round(unresolved_ratio, 3)}})
    if confidence_scores and (sum(confidence_scores) / count) < 0.50:
        report_penalties.append({"code": "LOW_REPORT_CONFIDENCE", "value": 3, "evidence": {"mean_confidence": round(sum(confidence_scores) / count, 3)}})

    report_penalty_total = sum(item["value"] for item in report_penalties)
    report_score = round(_clamp(report_score - report_penalty_total, 0, 100), 2)
    report_confidence = round((sum(confidence_scores) / count if confidence_scores else 0.0) * (len(final_scores) / count), 3)

    return {
        "scoring_config_version": config_version,
        "report_trust_score": report_score,
        "confidence_score": report_confidence,
        "overall_label": _label_from_score(report_score, thresholds),
        "summary": {
            "total_citations": len(citations),
            "verified": len([r for r in metadata_records if normalize_metadata_status(r.verification_status) == MetadataStatus.VERIFIED]),
            "partial": len([r for r in metadata_records if normalize_metadata_status(r.verification_status) == MetadataStatus.PARTIAL_MATCH]),
            "ambiguous": len([r for r in metadata_records if normalize_metadata_status(r.verification_status) == MetadataStatus.AMBIGUOUS]),
            "not_found": len([r for r in metadata_records if normalize_metadata_status(r.verification_status) == MetadataStatus.NOT_FOUND]),
            "provider_unavailable": len([r for r in metadata_records if normalize_metadata_status(r.verification_status) == MetadataStatus.PROVIDER_UNAVAILABLE]),
            "url_only": len([r for r in metadata_records if normalize_metadata_status(r.verification_status) == MetadataStatus.URL_ONLY]),
            "invalid_identifier": len([r for r in metadata_records if normalize_metadata_status(r.verification_status) == MetadataStatus.INVALID_IDENTIFIER]),
            "critical_warnings": len([w for w in all_warnings if w["severity"] == "critical"]),
            "high_warnings": len([w for w in all_warnings if w["severity"] == "high"]),
            "medium_warnings": len([w for w in all_warnings if w["severity"] == "medium"]),
            "low_warnings": len([w for w in all_warnings if w["severity"] == "low"]),
        },
        "report_penalty": {"total": report_penalty_total, "items": report_penalties},
        "component_summary": {
            "c1_metadata_completeness": round(totals["c1"] / count, 2),
            "c2_metadata_verification": round(totals["c2"] / count, 2),
            "c3_source_credibility": round(totals["c3"] / count, 2),
            "c4_relevance": round(totals["c4"] / count, 2),
            "c5_recency": round(totals["c5"] / count, 2),
            "c6_citation_style": round(totals["c6"] / count, 2),
            "c7_duplicate_concentration": round(totals["c7"] / count, 2),
        },
        "citations": citation_payloads,
        "warnings": all_warnings,
    }
