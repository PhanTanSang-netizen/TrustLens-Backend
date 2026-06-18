import os
from typing import Any

import httpx

from app.processing.metadata.metadata_matcher import MetadataCandidate


OPENALEX_BASE_URL = "https://api.openalex.org"


def _extract_authors(work: dict[str, Any]) -> str | None:
    authorships = work.get("authorships")

    if not isinstance(authorships, list):
        return None

    names: list[str] = []

    for authorship in authorships:
        if not isinstance(authorship, dict):
            continue

        author = authorship.get("author")

        if isinstance(author, dict) and author.get("display_name"):
            names.append(str(author["display_name"]))

    return ", ".join(names) if names else None


def _extract_venue(work: dict[str, Any]) -> str | None:
    primary_location = work.get("primary_location")

    if isinstance(primary_location, dict):
        source = primary_location.get("source")

        if isinstance(source, dict) and source.get("display_name"):
            return str(source["display_name"])

    host_venue = work.get("host_venue")

    if isinstance(host_venue, dict) and host_venue.get("display_name"):
        return str(host_venue["display_name"])

    return None


def _extract_source_url(work: dict[str, Any]) -> str | None:
    if work.get("doi"):
        return str(work["doi"])

    primary_location = work.get("primary_location")

    if isinstance(primary_location, dict):
        landing_page_url = primary_location.get("landing_page_url")
        pdf_url = primary_location.get("pdf_url")

        if landing_page_url:
            return str(landing_page_url)

        if pdf_url:
            return str(pdf_url)

    return work.get("id")


def _openalex_work_to_candidate(
    work: dict[str, Any],
) -> MetadataCandidate:
    cited_by_count = work.get("cited_by_count")
    if not isinstance(cited_by_count, int):
        cited_by_count = None

    return MetadataCandidate(
        provider="OpenAlex",
        source_url=_extract_source_url(work),
        doi=str(work.get("doi")).replace("https://doi.org/", "").lower()
        if work.get("doi")
        else None,
        title=work.get("display_name"),
        authors=_extract_authors(work),
        year=work.get("publication_year")
        if isinstance(work.get("publication_year"), int)
        else None,
        venue=_extract_venue(work),
        publisher=None,
        source_type=str(work.get("type") or "unknown"),
        citation_count=cited_by_count,
        raw_response=work,
    )


def search_openalex_by_title(
    title: str | None,
    year: int | None = None,
    rows: int = 5,
    timeout: float = 10.0,
) -> list[MetadataCandidate]:
    if not title or not title.strip():
        return []

    params: dict[str, Any] = {
        "search": title.strip(),
        "per-page": rows,
    }

    if year:
        params["filter"] = f"publication_year:{year}"

    api_key = os.getenv("OPENALEX_API_KEY")

    if api_key:
        params["api_key"] = api_key

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(
                f"{OPENALEX_BASE_URL}/works",
                params=params,
                headers={
                    "User-Agent": "TrustLens-MVP/1.0",
                    "Accept": "application/json",
                },
            )

        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        if not isinstance(results, list):
            return []

        return [
            _openalex_work_to_candidate(work)
            for work in results
            if isinstance(work, dict)
        ]

    except (httpx.RequestError, httpx.HTTPStatusError, ValueError):
        return []