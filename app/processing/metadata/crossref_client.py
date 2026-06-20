from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.processing.metadata.metadata_matcher import MetadataCandidate


CROSSREF_BASE_URL = "https://api.crossref.org"


@dataclass
class ProviderLookupResult:
    status: str
    provider: str
    http_status: int | None
    data: MetadataCandidate | None
    error_code: str | None


def _first_text(value: Any) -> str | None:
    if isinstance(value, list) and value:
        first = value[0]
        return str(first) if first is not None else None

    if value is None:
        return None

    return str(value)


def _extract_year(message: dict[str, Any]) -> int | None:
    for key in [
        "published-print",
        "published-online",
        "published",
        "created",
        "issued",
    ]:
        date_parts = message.get(key, {}).get("date-parts")

        if (
            isinstance(date_parts, list)
            and date_parts
            and isinstance(date_parts[0], list)
            and date_parts[0]
        ):
            try:
                return int(date_parts[0][0])
            except (TypeError, ValueError):
                continue

    return None


def _extract_authors(message: dict[str, Any]) -> str | None:
    authors = message.get("author")

    if not isinstance(authors, list):
        return None

    names: list[str] = []

    for author in authors:
        if not isinstance(author, dict):
            continue

        given = author.get("given")
        family = author.get("family")

        if given and family:
            names.append(f"{given} {family}")
        elif family:
            names.append(str(family))

    return ", ".join(names) if names else None


def _crossref_message_to_candidate(
    message: dict[str, Any],
) -> MetadataCandidate:
    doi = message.get("DOI")
    title = _first_text(message.get("title"))
    venue = _first_text(message.get("container-title"))
    publisher = message.get("publisher")
    year = _extract_year(message)
    authors = _extract_authors(message)
    source_url = message.get("URL")
    source_type = message.get("type") or "unknown"

    citation_count = message.get("is-referenced-by-count")
    if not isinstance(citation_count, int):
        citation_count = None

    return MetadataCandidate(
        provider="Crossref",
        source_url=source_url,
        doi=str(doi).lower() if doi else None,
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        publisher=str(publisher) if publisher else None,
        source_type=str(source_type),
        citation_count=citation_count,
        raw_response=message,
    )


def lookup_crossref_by_doi(
    doi: str,
    timeout: float = 10.0,
) -> MetadataCandidate | None:
    result = lookup_crossref_by_doi_result(doi=doi, timeout=timeout)
    return result.data if result.status == "SUCCESS" else None


def lookup_crossref_by_doi_result(
    doi: str,
    timeout: float = 10.0,
) -> ProviderLookupResult:
    if not doi:
        return ProviderLookupResult(
            status="INVALID_RESPONSE",
            provider="Crossref",
            http_status=None,
            data=None,
            error_code="DOI_EMPTY",
        )

    encoded_doi = quote(doi.strip(), safe="")
    url = f"{CROSSREF_BASE_URL}/works/{encoded_doi}"
    mailto = settings.CROSSREF_MAILTO

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(
                url,
                headers={
                    "User-Agent": f"TrustLens/1.2 (mailto:{mailto})",
                    "Accept": "application/json",
                },
            )

        if response.status_code == 404:
            return ProviderLookupResult(
                status="NOT_FOUND",
                provider="Crossref",
                http_status=404,
                data=None,
                error_code=None,
            )

        if response.status_code == 429:
            return ProviderLookupResult(
                status="RATE_LIMITED",
                provider="Crossref",
                http_status=429,
                data=None,
                error_code="HTTP_429",
            )

        response.raise_for_status()

        data = response.json()
        message = data.get("message")

        if not isinstance(message, dict):
            return ProviderLookupResult(
                status="INVALID_RESPONSE",
                provider="Crossref",
                http_status=response.status_code,
                data=None,
                error_code="MESSAGE_MISSING",
            )

        return ProviderLookupResult(
            status="SUCCESS",
            provider="Crossref",
            http_status=response.status_code,
            data=_crossref_message_to_candidate(message),
            error_code=None,
        )

    except httpx.HTTPStatusError as exc:
        return ProviderLookupResult(
            status="UNAVAILABLE",
            provider="Crossref",
            http_status=exc.response.status_code,
            data=None,
            error_code=f"HTTP_{exc.response.status_code}",
        )
    except httpx.RequestError as exc:
        return ProviderLookupResult(
            status="UNAVAILABLE",
            provider="Crossref",
            http_status=None,
            data=None,
            error_code=exc.__class__.__name__,
        )
    except ValueError:
        return ProviderLookupResult(
            status="INVALID_RESPONSE",
            provider="Crossref",
            http_status=None,
            data=None,
            error_code="JSON_DECODE_FAILED",
        )


def search_crossref_by_title(
    title: str | None,
    year: int | None = None,
    rows: int = 5,
    timeout: float = 10.0,
) -> list[MetadataCandidate]:
    if not title or not title.strip():
        return []

    params: dict[str, Any] = {
        "query.bibliographic": title.strip(),
        "rows": rows,
    }

    if year:
        params["filter"] = f"from-pub-date:{year},until-pub-date:{year}"

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(
                f"{CROSSREF_BASE_URL}/works",
                params=params,
                headers={
                    "User-Agent": f"TrustLens/1.2 (mailto:{settings.CROSSREF_MAILTO})",
                    "Accept": "application/json",
                },
            )

        response.raise_for_status()

        data = response.json()
        items = data.get("message", {}).get("items", [])

        if not isinstance(items, list):
            return []

        return [
            _crossref_message_to_candidate(item)
            for item in items
            if isinstance(item, dict)
        ]

    except (httpx.RequestError, httpx.HTTPStatusError, ValueError):
        return []
