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

    if re.search(r"\((19|20)\d{2}\)", normalized[:160]):
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
    match = re.search(r"https?://[^\s]+", text)

    if not match:
        return None

    return match.group(0).rstrip(".,")


def extract_doi(text: str) -> str | None:
    match = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", text, re.IGNORECASE)

    if not match:
        return None

    return match.group(0).rstrip(".,")


def detect_style(text: str) -> str:
    if re.match(r"^\[\d+\]", text.strip()):
        return "IEEE"

    if re.search(r"\((19|20)\d{2}\)", text[:160]):
        return "AUTHOR_YEAR"

    if re.match(r"^\d+[\.\)]\s+", text.strip()):
        return "NUMBERED"

    return "UNKNOWN"


def extract_authors(text: str) -> str | None:
    match = re.match(r"^(.*?)\s*\((19|20)\d{2}\)", text)

    if not match:
        return None

    authors = match.group(1).strip(" ,.")

    return authors or None


def extract_title(text: str) -> str | None:
    match = re.search(r"\((19|20)\d{2}\)\s*,?\s*(.*)", text)

    if not match:
        return None

    after_year = match.group(2).strip()

    if not after_year:
        return None

    after_year = re.sub(r"\s+", " ", after_year)

    title = re.split(
        r"\.\s*Truy\s*cập|,\s*Truy\s*cập|\s+Truy\s*cập|,\s*(?:NXB|Nhà xuất bản)|https?://",
        after_year,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]

    title = title.strip(" ,.")

    return title or None

def split_reference_entries(raw_text: str) -> list[str]:
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

    return entries


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