from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

import httpx

from app.models.citation import Citation
from app.processing.metadata.url_checker import check_url_exists


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


def _similarity(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left.lower(), right.lower()).ratio()


def _crossref_item(citation: Citation, item: dict, query_type: str, query_value: str) -> ResolvedMetadata:
    title = (item.get("title") or [None])[0]
    year = ((item.get("issued", {}).get("date-parts") or [[None]])[0] or [None])[0]
    doi = item.get("DOI")
    title_similarity = _similarity(citation.title, title)
    doi_match = bool(citation.doi and doi and citation.doi.lower() == doi.lower())
    confidence = 1.0 if doi_match else min(0.95, title_similarity)
    status = "verified" if doi_match or confidence >= 0.82 else "partial" if confidence >= 0.62 else "ambiguous"
    return ResolvedMetadata(
        provider="CROSSREF",
        query_type=query_type,
        query_value=query_value,
        source_url=item.get("URL"),
        matched_title=title,
        matched_year=year,
        verification_status=status,
        confidence_score=round(confidence, 3),
        raw_response={
            "doi": doi,
            "type": item.get("type"),
            "publisher": item.get("publisher"),
            "container_title": (item.get("container-title") or [None])[0],
            "evidence": {"title_similarity": round(title_similarity, 3), "doi_match": doi_match},
        },
    )


def resolve_citation_metadata(citation: Citation) -> ResolvedMetadata:
    try:
        with httpx.Client(timeout=httpx.Timeout(connect=4, read=10, write=4, pool=4), follow_redirects=True) as client:
            if citation.doi:
                response = client.get(f"https://api.crossref.org/works/{citation.doi}")
                if response.status_code == 404:
                    return ResolvedMetadata("CROSSREF", "doi", citation.doi, None, None, None, "not_found", 0.0, {"status_code": 404})
                response.raise_for_status()
                return _crossref_item(citation, response.json().get("message", {}), "doi", citation.doi)
            if citation.title:
                response = client.get("https://api.crossref.org/works", params={"query.title": citation.title, "rows": 1})
                response.raise_for_status()
                items = response.json().get("message", {}).get("items", [])
                if items:
                    return _crossref_item(citation, items[0], "title", citation.title)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {404, 410}:
            return ResolvedMetadata("CROSSREF", "doi" if citation.doi else "title", citation.doi or citation.title, None, None, None, "not_found", 0.0, {"status_code": exc.response.status_code})
    except httpx.RequestError as exc:
        return ResolvedMetadata("CROSSREF", "doi" if citation.doi else "title", citation.doi or citation.title, None, None, None, "unknown", 0.0, {"error": str(exc), "provider_error": True})

    url_check = check_url_exists(citation.url)
    status = "partial" if citation.url and url_check.verification_status == "URL_OK" else "unknown"
    return ResolvedMetadata(
        "URL_CHECK",
        "url",
        citation.url,
        url_check.final_url,
        citation.title,
        citation.year,
        status,
        0.45 if status == "partial" else 0.0,
        {"url_status": url_check.verification_status, "status_code": url_check.status_code, "error": url_check.error},
    )
