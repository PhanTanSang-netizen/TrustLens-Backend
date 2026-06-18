from dataclasses import dataclass
import re


@dataclass
class ParsedCitation:
    sequence_no: int
    raw_text: str
    detected_style: str
    authors: str | None = None
    title: str | None = None
    year: int | None = None
    doi: str | None = None
    url: str | None = None


def is_new_citation_line(line: str) -> bool:
    normalized = line.strip()

    if not normalized:
        return False

    if re.match(r"^(\[\d+\]|\d+[\.\)])\s+", normalized):
        return True

    if re.search(r"\((19|20)\d{2}\)", normalized[:180]):
        return True

    return False


def clean_citation_prefix(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^\[\d+\]\s*", "", text)
    text = re.sub(r"^\d+[\.\)]\s*", "", text)
    return text.strip()


def extract_year(text: str) -> int | None:
    match = re.search(r"\((19|20)\d{2}\)", text)

    if match:
        return int(match.group(0).strip("()"))

    match = re.search(r"\b(19|20)\d{2}\b", text)

    if match:
        return int(match.group(0))

    return None


def extract_url(text: str) -> str | None:
    match = re.search(r"https?://[^\s\]\)]+", text)

    if not match:
        return None

    return match.group(0).rstrip(".,;)")


def extract_doi(text: str) -> str | None:
    match = re.search(
        r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(0).rstrip(".,;)")


def detect_style(text: str) -> str:
    normalized = text.strip()

    if re.match(r"^\[\d+\]", normalized):
        return "IEEE"

    if re.match(r"^\d+[\.\)]\s+", normalized):
        return "NUMBERED"

    if re.search(r"\((19|20)\d{2}\)", normalized[:180]):
        return "AUTHOR_YEAR"

    return "UNKNOWN"


def extract_authors(text: str) -> str | None:
    cleaned = clean_citation_prefix(text)

    match = re.match(r"^(.*?)\s*\((19|20)\d{2}\)", cleaned)
    if match:
        authors = match.group(1).strip(" ,.")
        return authors or None

    match = re.match(r"^(.*?),\s*[\"“]", cleaned)
    if match:
        authors = match.group(1).strip(" ,.")
        return authors or None

    first_part = cleaned.split(".", 1)[0].strip(" ,.")
    if 2 <= len(first_part.split()) <= 12:
        return first_part

    return None


def extract_title_from_author_year(text: str) -> str | None:
    match = re.search(r"\((19|20)\d{2}\)\s*[\.,]?\s*(.*)", text)

    if not match:
        return None

    after_year = match.group(2).strip()

    if not after_year:
        return None

    after_year = re.sub(r"\s+", " ", after_year)

    title = re.split(
        r"\.\s*Truy\s*cập|,\s*Truy\s*cập|\s+Truy\s*cập|"
        r",\s*(?:NXB|Nhà xuất bản)|https?://|doi\.org|DOI:",
        after_year,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]

    title = title.strip(" ,.\"“”")

    return title or None


def extract_title_from_quoted_text(text: str) -> str | None:
    match = re.search(r"[\"“](.*?)[\"”]", text)

    if not match:
        return None

    title = match.group(1).strip(" ,.\"“”")

    return title or None


def extract_title_generic(text: str) -> str | None:
    cleaned = clean_citation_prefix(text)

    cleaned = re.sub(r"https?://[^\s]+", "", cleaned)
    cleaned = re.sub(
        r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    cleaned = re.sub(r"^.*?\((19|20)\d{2}\)\s*[\.,]?\s*", "", cleaned)

    parts = [
        part.strip(" ,.\"“”")
        for part in cleaned.split(".")
        if part.strip(" ,.\"“”")
    ]

    if not parts:
        return None

    for part in parts:
        word_count = len(part.split())
        if 3 <= word_count <= 25:
            return part

    return None


def extract_title(text: str) -> str | None:
    return (
        extract_title_from_quoted_text(text)
        or extract_title_from_author_year(text)
        or extract_title_generic(text)
    )


def split_reference_entries(raw_text: str) -> list[str]:
    if not raw_text or not raw_text.strip():
        return []

    lines = [
        line.strip()
        for line in raw_text.splitlines()
        if line.strip()
    ]

    entries: list[str] = []
    current_parts: list[str] = []

    for line in lines:
        if is_new_citation_line(line):
            if current_parts:
                entries.append(" ".join(current_parts).strip())

            current_parts = [line]
        else:
            if current_parts:
                current_parts.append(line)
            else:
                current_parts = [line]

    if current_parts:
        entries.append(" ".join(current_parts).strip())

    return [
        entry
        for entry in entries
        if entry and len(entry.split()) >= 3
    ]


def parse_citations_from_reference_text(raw_text: str) -> list[ParsedCitation]:
    if not raw_text or not raw_text.strip():
        return []

    entries = split_reference_entries(raw_text)

    parsed_citations: list[ParsedCitation] = []

    for index, entry in enumerate(entries, start=1):
        cleaned_text = clean_citation_prefix(entry)

        parsed_citations.append(
            ParsedCitation(
                sequence_no=index,
                raw_text=cleaned_text,
                detected_style=detect_style(entry),
                authors=extract_authors(cleaned_text),
                title=extract_title(cleaned_text),
                year=extract_year(cleaned_text),
                doi=extract_doi(cleaned_text),
                url=extract_url(cleaned_text),
            )
        )

    return parsed_citations