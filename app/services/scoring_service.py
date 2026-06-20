from collections import Counter
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.citation import Citation
from app.models.metadata_record import MetadataRecord
from app.models.trust_score import CitationScore
from app.models.warning import Warning


SCORING_VERSION = "trust-score-v1.0"


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _warning(code: str, severity: str, message: str, recommendation: str, evidence: dict | None = None) -> dict:
    return {"code": code, "severity": severity, "message": message, "recommendation": recommendation, "evidence": evidence or {}}


def _source_type(metadata: MetadataRecord | None, citation: Citation) -> str:
    raw = metadata.raw_response if metadata is not None and metadata.raw_response else {}
    raw_type = raw.get("type")
    if raw_type == "journal-article":
        return "journal"
    if raw_type == "proceedings-article":
        return "conference"
    if raw_type:
        return str(raw_type)
    if citation.url and any(domain in citation.url.lower() for domain in ["medium.com", "wordpress", "blogspot"]):
        return "blog"
    if citation.url:
        return "website"
    return "unknown"


def _relevance_score(title: str | None, document_text: str) -> float:
    if not title:
        return 7.0
    title_tokens = {token for token in title.lower().split() if len(token) > 3}
    doc_tokens = {token for token in document_text[:8000].lower().split() if len(token) > 3}
    if not title_tokens or not doc_tokens:
        return 7.0
    return round(_clamp(len(title_tokens & doc_tokens) / len(title_tokens) * 28, 5, 20), 2)


def score_submission(
    db: Session,
    submission_id: UUID,
    citations: list[Citation],
    metadata_records: list[MetadataRecord],
    document_text: str,
    expected_style: str | None,
) -> dict:
    if citations:
        db.execute(delete(CitationScore).where(CitationScore.citation_id.in_([citation.id for citation in citations])))
    db.execute(delete(Warning).where(Warning.submission_id == submission_id))

    metadata_by_citation = {record.citation_id: record for record in metadata_records}
    duplicate_keys: dict[str, UUID] = {}
    source_counter = Counter(_source_type(metadata_by_citation.get(citation.id), citation) for citation in citations)
    current_year = datetime.now(timezone.utc).year

    citation_payloads = []
    all_warnings = []
    totals = Counter()
    score_total = 0.0
    confidence_total = 0.0

    for citation in citations:
        metadata = metadata_by_citation.get(citation.id)
        warnings = []
        present = {
            "authors": bool(citation.authors),
            "title": bool(citation.title),
            "year": citation.year is not None,
            "doi_or_url": bool(citation.doi or citation.url),
        }
        c1 = round(sum(present.values()) / len(present) * 10, 2)
        missing = [key for key, value in present.items() if not value]
        if missing:
            warnings.append(_warning("MISSING_REQUIRED_FIELD", "medium", "Citation is missing required fields.", "Add missing citation fields.", {"missing_fields": missing}))

        status = metadata.verification_status if metadata is not None else "unknown"
        confidence = metadata.confidence_score if metadata is not None else 0.0
        c2 = {"verified": 20, "partial": 12, "ambiguous": 8, "not_found": 2, "unknown": 5}.get(status, 5)
        if status == "not_found":
            warnings.append(_warning("SOURCE_NOT_FOUND", "high", "No reliable metadata match was found.", "Check DOI/title or replace the source."))
        if status == "unknown":
            warnings.append(_warning("PROVIDER_UNAVAILABLE", "medium", "Metadata provider could not provide enough evidence.", "Retry later or verify manually."))

        source_type = _source_type(metadata, citation)
        c3 = {"journal": 20, "conference": 18, "book": 16, "posted-content": 12, "website": 8, "blog": 3, "unknown": 7}.get(source_type, 10)
        if c3 <= 8:
            warnings.append(_warning("LOW_CREDIBILITY_SOURCE", "high" if c3 <= 5 else "medium", "Source has limited academic credibility evidence.", "Prefer academic or institutional sources.", {"source_type": source_type}))

        c4 = _relevance_score(citation.title, document_text)
        if c4 < 8:
            warnings.append(_warning("LOW_RELEVANCE", "medium", "Citation appears weakly related to the report topic.", "Check topic relevance."))

        if citation.year is None:
            c5 = 4
        else:
            age = max(0, current_year - citation.year)
            c5 = 10 if age <= 5 else 7 if age <= 10 else 3
            if age > 10:
                warnings.append(_warning("OUTDATED_REFERENCE", "medium", "Reference is older than 10 years.", "Use a newer source unless foundational.", {"age": age}))

        detected_style = citation.detected_style or "UNKNOWN"
        if expected_style and expected_style.upper() not in {detected_style.upper(), "UNKNOWN"}:
            c6 = 6
            warnings.append(_warning("STYLE_MISMATCH", "low", "Citation style differs from requirement.", "Normalize to required style.", {"expected_style": expected_style, "detected_style": detected_style}))
        else:
            c6 = 9 if detected_style != "UNKNOWN" else 5

        key = (citation.doi or citation.url or citation.title or "").strip().lower()
        if key and key in duplicate_keys:
            c7 = 1
            warnings.append(_warning("DUPLICATE_REFERENCE", "medium", "Duplicate reference detected.", "Merge or remove duplicate.", {"duplicate_of": str(duplicate_keys[key])}))
        else:
            if key:
                duplicate_keys[key] = citation.id
            c7 = 5 if source_counter[source_type] <= max(1, len(citations) // 2) else 3

        severe = len([item for item in warnings if item["severity"] in {"high", "critical"}])
        c8 = max(1, 5 - severe * 2) if severe else 5
        reference_score = round(_clamp(c1 + c2 + c3 + c4 + c5 + c6 + c7 + c8, 0, 100), 2)
        citation_confidence = round(_clamp((confidence + c1 / 10 + (1 if detected_style != "UNKNOWN" else 0.5)) / 3, 0, 1), 3)
        explanations = {f"c{i}": {"score": score} for i, score in enumerate([c1, c2, c3, c4, c5, c6, c7, c8], start=1)}

        db.add(CitationScore(citation_id=citation.id, scoring_config_version=SCORING_VERSION, c1=c1, c2=c2, c3=c3, c4=c4, c5=c5, c6=c6, c7=c7, c8=c8, reference_trust_score=reference_score, confidence_score=citation_confidence, explanations=explanations))
        for warning in warnings:
            db.add(Warning(submission_id=submission_id, citation_id=citation.id, code=warning["code"], severity=warning["severity"], message=warning["message"], recommendation=warning["recommendation"], evidence=warning["evidence"]))

        raw_metadata = metadata.raw_response if metadata is not None and metadata.raw_response else {}
        citation_payloads.append({
            "citation_id": str(citation.id),
            "raw_text": citation.raw_text,
            "normalized_fields": {"title": citation.title, "authors": citation.authors, "year": citation.year, "doi": citation.doi, "url": citation.url, "venue": raw_metadata.get("container_title") or raw_metadata.get("publisher")},
            "metadata": {"provider": metadata.provider.lower() if metadata is not None else "unknown", "match_status": status, "match_confidence": confidence, "source_type": source_type, "evidence": raw_metadata.get("evidence", {})},
            "scores": {"c1": c1, "c2": c2, "c3": c3, "c4": c4, "c5": c5, "c6": c6, "c7": c7, "c8": c8, "reference_trust_score": reference_score, "confidence_score": citation_confidence},
            "warnings": warnings,
        })
        all_warnings.extend(warnings)
        score_total += reference_score
        confidence_total += citation_confidence
        for key_name, value in {"c1": c1, "c2": c2, "c3": c3, "c4": c4, "c5": c5, "c6": c6, "c7": c7, "c8": c8}.items():
            totals[key_name] += value

    count = max(1, len(citations))
    report_score = round(score_total / count, 2)
    return {
        "scoring_config_version": SCORING_VERSION,
        "report_trust_score": report_score,
        "confidence_score": round(confidence_total / count, 3),
        "overall_label": "reliable" if report_score >= 85 else "acceptable" if report_score >= 70 else "needs_review" if report_score >= 50 else "high_risk",
        "summary": {
            "total_citations": len(citations),
            "verified": len([r for r in metadata_records if r.verification_status == "verified"]),
            "partial": len([r for r in metadata_records if r.verification_status == "partial"]),
            "not_found": len([r for r in metadata_records if r.verification_status == "not_found"]),
            "unknown": len([r for r in metadata_records if r.verification_status == "unknown"]),
            "critical_warnings": len([w for w in all_warnings if w["severity"] == "critical"]),
            "high_warnings": len([w for w in all_warnings if w["severity"] == "high"]),
            "medium_warnings": len([w for w in all_warnings if w["severity"] == "medium"]),
            "low_warnings": len([w for w in all_warnings if w["severity"] == "low"]),
        },
        "report_penalty": {"total": 0.0, "items": []},
        "component_summary": {
            "c1_metadata_completeness": round(totals["c1"] / count, 2),
            "c2_metadata_verification": round(totals["c2"] / count, 2),
            "c3_source_credibility": round(totals["c3"] / count, 2),
            "c4_relevance": round(totals["c4"] / count, 2),
            "c5_recency": round(totals["c5"] / count, 2),
            "c6_citation_quality": round(totals["c6"] / count, 2),
            "c7_source_diversity": round(totals["c7"] / count, 2),
            "c8_academic_risk_integrity": round(totals["c8"] / count, 2),
        },
        "citations": citation_payloads,
        "warnings": all_warnings,
    }
