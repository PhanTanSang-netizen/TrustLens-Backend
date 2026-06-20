from dataclasses import dataclass
import re
from typing import Any


@dataclass
class ReportChunk:
    chunk_id: str
    text: str
    heading: str | None
    start_char: int
    end_char: int


PII_PATTERNS = [
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE), "[EMAIL]"),
    (re.compile(r"\b\d{8,12}\b"), "[ID]"),
]


def sanitize_text(text: str | None) -> str:
    sanitized = text or ""
    for pattern, replacement in PII_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


def build_report_core_context(
    report_text: str | None = None,
    report_context: dict[str, Any] | None = None,
) -> tuple[str, str]:
    context = report_context if isinstance(report_context, dict) else {}
    parts = [
        context.get("assignment_title"),
        context.get("assignment_description"),
        context.get("report_title"),
        context.get("report_abstract"),
        context.get("introduction"),
        context.get("conclusion"),
    ]
    method = "structured"
    if not any(parts):
        body = str(context.get("body_text") or report_text or "")
        paragraphs = [item.strip() for item in re.split(r"\n\s*\n", body) if item.strip()]
        head = paragraphs[:4]
        tail = paragraphs[-2:] if len(paragraphs) > 4 else []
        parts = [context.get("assignment_title"), context.get("assignment_description"), *head, *tail]
        method = "heuristic"
    return sanitize_text("\n".join(str(part) for part in parts if part)).strip(), method


def build_reference_representation(
    title: str | None,
    abstract: str | None = None,
    keywords: list[str] | str | None = None,
    venue: str | None = None,
) -> tuple[str, dict[str, bool]]:
    if isinstance(keywords, list):
        keyword_text = ", ".join(str(item) for item in keywords)
    else:
        keyword_text = str(keywords) if keywords else None
    parts = [
        f"Title: {title}" if title else None,
        f"Abstract: {abstract}" if abstract else None,
        f"Keywords: {keyword_text}" if keyword_text else None,
        f"Venue: {venue}" if venue else None,
    ]
    evidence = {
        "reference_has_title": bool(title),
        "reference_has_abstract": bool(abstract),
        "reference_has_keywords": bool(keyword_text),
        "reference_has_venue": bool(venue),
    }
    return sanitize_text("\n".join(part for part in parts if part)).strip(), evidence


def chunk_report_text(
    text: str | None,
    target_tokens: int = 320,
    overlap_tokens: int = 48,
    min_tokens: int = 80,
    max_chunks: int = 64,
) -> list[ReportChunk]:
    body = sanitize_text(text)
    if not body.strip():
        return []

    paragraph_matches = list(re.finditer(r"\S(?:.*?)(?:\n\s*\n|$)", body, flags=re.DOTALL))
    chunks: list[ReportChunk] = []
    current_heading: str | None = None
    pending: list[tuple[str, int, int]] = []

    def flush_pending() -> None:
        nonlocal pending
        if not pending:
            return
        combined = "\n\n".join(item[0] for item in pending).strip()
        start = pending[0][1]
        end = pending[-1][2]
        for split_text, split_start, split_end in _split_long_text(combined, start, target_tokens, overlap_tokens):
            token_count = len(_tokens(split_text))
            if token_count >= min_tokens or not chunks:
                chunks.append(
                    ReportChunk(
                        chunk_id=f"chunk-{len(chunks) + 1}",
                        text=split_text,
                        heading=current_heading,
                        start_char=split_start,
                        end_char=split_end,
                    )
                )
            if len(chunks) >= max_chunks:
                break
        pending = []

    for match in paragraph_matches:
        paragraph = match.group(0).strip()
        if not paragraph:
            continue
        if _looks_like_heading(paragraph):
            flush_pending()
            current_heading = paragraph[:120]
            continue
        pending.append((paragraph, match.start(), match.end()))
        if len(_tokens(" ".join(item[0] for item in pending))) >= target_tokens:
            flush_pending()
        if len(chunks) >= max_chunks:
            break

    flush_pending()
    return chunks[:max_chunks]


def _tokens(text: str) -> list[str]:
    return re.findall(r"\S+", text)


def _looks_like_heading(paragraph: str) -> bool:
    if len(paragraph) > 120 or "\n" in paragraph:
        return False
    return bool(re.match(r"^(\d+(\.\d+)*\.?\s+)?[A-ZÀ-Ỹ][^\.\?!]{2,}$", paragraph.strip()))


def _split_long_text(
    text: str,
    absolute_start: int,
    target_tokens: int,
    overlap_tokens: int,
) -> list[tuple[str, int, int]]:
    tokens = list(re.finditer(r"\S+", text))
    if len(tokens) <= target_tokens:
        return [(text, absolute_start, absolute_start + len(text))]

    result: list[tuple[str, int, int]] = []
    cursor = 0
    step = max(1, target_tokens - overlap_tokens)
    while cursor < len(tokens):
        window = tokens[cursor : cursor + target_tokens]
        if not window:
            break
        start = window[0].start()
        end = window[-1].end()
        result.append((text[start:end], absolute_start + start, absolute_start + end))
        if cursor + target_tokens >= len(tokens):
            break
        cursor += step
    return result
