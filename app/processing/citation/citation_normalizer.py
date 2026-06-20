from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import re
import unicodedata


@dataclass
class NormalizedCitationFields:
    raw_text: str
    authors: str | None
    title: str | None
    year: int | None
    doi: str | None
    url: str | None
    identity_key: str


TRACKING_QUERY_PREFIXES = (
    "utm_",
)

TRACKING_QUERY_NAMES = {
    "fbclid",
    "gclid",
    "yclid",
    "mc_cid",
    "mc_eid",
}


def normalize_whitespace(text: str | None) -> str | None:
    if text is None:
        return None

    normalized = re.sub(r"\s+", " ", text).strip()

    return normalized or None


def strip_trailing_punctuation(text: str | None) -> str | None:
    if text is None:
        return None

    cleaned = text.strip().rstrip(".,;:)]}")

    return cleaned or None


def remove_surrounding_quotes(text: str | None) -> str | None:
    if text is None:
        return None

    cleaned = text.strip().strip("\"'“”‘’")

    return cleaned or None


def normalize_author_text(authors: str | None) -> str | None:
    authors = normalize_whitespace(authors)

    if not authors:
        return None

    authors = authors.strip(" ,.;")
    authors = re.sub(r"\s*&\s*", " & ", authors)
    authors = re.sub(r"\s+and\s+", " and ", authors, flags=re.IGNORECASE)

    return authors or None


def normalize_title_for_display(title: str | None) -> str | None:
    title = normalize_whitespace(title)
    title = remove_surrounding_quotes(title)

    if not title:
        return None

    title = title.strip(" ,.;:")

    return title or None


def normalize_doi(doi: str | None) -> str | None:
    doi = normalize_whitespace(doi)

    if not doi:
        return None

    doi = doi.strip()
    doi = doi.replace("https://doi.org/", "")
    doi = doi.replace("http://doi.org/", "")
    doi = doi.replace("https://dx.doi.org/", "")
    doi = doi.replace("http://dx.doi.org/", "")
    doi = re.sub(r"^doi\s*:\s*", "", doi, flags=re.IGNORECASE)
    doi = strip_trailing_punctuation(doi)
    doi = doi.lower() if doi else None

    if not doi:
        return None

    if not re.match(r"^10\.\d{4,9}/\S+$", doi, flags=re.IGNORECASE):
        return None

    return doi


def normalize_url(url: str | None) -> str | None:
    url = normalize_whitespace(url)

    if not url:
        return None

    url = strip_trailing_punctuation(url)

    if not url:
        return None

    if url.startswith("www."):
        url = f"https://{url}"

    if not re.match(r"^https?://", url, flags=re.IGNORECASE):
        return None

    parts = urlsplit(url)

    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()

    path = parts.path.rstrip("/")

    filtered_query_items = []

    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        key_lower = key.lower()

        if key_lower in TRACKING_QUERY_NAMES:
            continue

        if any(key_lower.startswith(prefix) for prefix in TRACKING_QUERY_PREFIXES):
            continue

        filtered_query_items.append((key, value))

    query = urlencode(filtered_query_items, doseq=True)

    normalized = urlunsplit(
        (
            scheme,
            netloc,
            path,
            query,
            "",
        )
    )

    return normalized or None


def normalize_year(year: int | str | None) -> int | None:
    if year is None:
        return None

    try:
        parsed_year = int(year)
    except (TypeError, ValueError):
        return None

    if parsed_year < 1800 or parsed_year > 2100:
        return None

    return parsed_year


def _remove_vietnamese_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)

    return "".join(
        char
        for char in normalized
        if unicodedata.category(char) != "Mn"
    )


def normalize_text_key(text: str | None) -> str | None:
    text = normalize_whitespace(text)

    if not text:
        return None

    text = _remove_vietnamese_accents(text)
    text = text.lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\b10\.\d{4,9}/\S+\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text or None


def build_citation_identity_key(
    raw_text: str | None = None,
    authors: str | None = None,
    title: str | None = None,
    year: int | None = None,
    doi: str | None = None,
    url: str | None = None,
) -> str:
    normalized_doi = normalize_doi(doi)
    normalized_url = normalize_url(url)
    normalized_title_key = normalize_text_key(title)
    normalized_authors_key = normalize_text_key(authors)
    normalized_raw_key = normalize_text_key(raw_text)

    if normalized_doi:
        return f"doi:{normalized_doi}"

    if normalized_url:
        return f"url:{normalized_url}"

    if normalized_title_key and year:
        author_part = normalized_authors_key or "unknown_author"
        return f"title_year:{normalized_title_key}|{year}|{author_part}"

    if normalized_raw_key:
        return f"raw:{normalized_raw_key}"

    return "unknown"


def normalize_citation_fields(
    raw_text: str,
    authors: str | None = None,
    title: str | None = None,
    year: int | str | None = None,
    doi: str | None = None,
    url: str | None = None,
) -> NormalizedCitationFields:
    normalized_raw_text = normalize_whitespace(raw_text) or ""
    normalized_authors = normalize_author_text(authors)
    normalized_title = normalize_title_for_display(title)
    normalized_year = normalize_year(year)
    normalized_doi = normalize_doi(doi)
    normalized_url = normalize_url(url)

    identity_key = build_citation_identity_key(
        raw_text=normalized_raw_text,
        authors=normalized_authors,
        title=normalized_title,
        year=normalized_year,
        doi=normalized_doi,
        url=normalized_url,
    )

    return NormalizedCitationFields(
        raw_text=normalized_raw_text,
        authors=normalized_authors,
        title=normalized_title,
        year=normalized_year,
        doi=normalized_doi,
        url=normalized_url,
        identity_key=identity_key,
    )


def get_object_or_dict_value(
    item: Any,
    field_name: str,
    default: Any = None,
) -> Any:
    if item is None:
        return default

    if isinstance(item, dict):
        return item.get(field_name, default)

    return getattr(item, field_name, default)


def get_citation_identity_key(
    citation: Any,
) -> str:
    return build_citation_identity_key(
        raw_text=get_object_or_dict_value(citation, "raw_text"),
        authors=get_object_or_dict_value(citation, "authors"),
        title=get_object_or_dict_value(citation, "title"),
        year=get_object_or_dict_value(citation, "year"),
        doi=get_object_or_dict_value(citation, "doi"),
        url=get_object_or_dict_value(citation, "url"),
    )


def detect_duplicate_citation_keys(
    citations: list[Any],
) -> dict[str, list[Any]]:
    groups: dict[str, list[Any]] = {}

    for citation in citations:
        key = get_citation_identity_key(citation)

        if key == "unknown":
            continue

        groups.setdefault(key, []).append(citation)

    return {
        key: value
        for key, value in groups.items()
        if len(value) > 1
    }