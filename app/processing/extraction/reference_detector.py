from dataclasses import dataclass
import re


@dataclass
class ReferenceSectionDetectionResult:
    heading: str
    raw_text: str
    start_index: int
    end_index: int
    detection_method: str


REFERENCE_HEADING_PATTERNS = [
    r"^\s*(?:\d+[\.\)]\s*)?(?:[ivxlcdm]+[\.\)]\s*)?(tài\s+liệu\s+tham\s+khảo)\s*:?\s*$",
    r"^\s*(?:\d+[\.\)]\s*)?(?:[ivxlcdm]+[\.\)]\s*)?(danh\s+mục\s+tài\s+liệu\s+tham\s+khảo)\s*:?\s*$",
    r"^\s*(?:\d+[\.\)]\s*)?(?:[ivxlcdm]+[\.\)]\s*)?(nguồn\s+tài\s+liệu\s+tham\s+khảo)\s*:?\s*$",
    r"^\s*(?:\d+[\.\)]\s*)?(?:[ivxlcdm]+[\.\)]\s*)?(nguồn\s+tham\s+khảo)\s*:?\s*$",
    r"^\s*(?:\d+[\.\)]\s*)?(?:[ivxlcdm]+[\.\)]\s*)?(references)\s*:?\s*$",
    r"^\s*(?:\d+[\.\)]\s*)?(?:[ivxlcdm]+[\.\)]\s*)?(reference\s+list)\s*:?\s*$",
    r"^\s*(?:\d+[\.\)]\s*)?(?:[ivxlcdm]+[\.\)]\s*)?(bibliography)\s*:?\s*$",
    r"^\s*(?:\d+[\.\)]\s*)?(?:[ivxlcdm]+[\.\)]\s*)?(works\s+cited)\s*:?\s*$",
]

STOP_HEADING_PATTERNS = [
    r"^\s*(?:\d+[\.\)]\s*)?(?:[ivxlcdm]+[\.\)]\s*)?(phụ\s+lục)\s*:?\s*$",
    r"^\s*(?:\d+[\.\)]\s*)?(?:[ivxlcdm]+[\.\)]\s*)?(appendix)\s*:?\s*$",
    r"^\s*(?:\d+[\.\)]\s*)?(?:[ivxlcdm]+[\.\)]\s*)?(lời\s+cảm\s+ơn)\s*:?\s*$",
    r"^\s*(?:\d+[\.\)]\s*)?(?:[ivxlcdm]+[\.\)]\s*)?(acknowledgements?)\s*:?\s*$",
]


def _find_last_reference_heading(full_text: str) -> re.Match[str] | None:
    compiled_patterns = [
        re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        for pattern in REFERENCE_HEADING_PATTERNS
    ]

    best_match: re.Match[str] | None = None

    for pattern in compiled_patterns:
        for match in pattern.finditer(full_text):
            if best_match is None or match.start() > best_match.start():
                best_match = match

    return best_match


def _find_next_stop_heading(
    full_text: str,
    start_position: int,
) -> int:
    compiled_patterns = [
        re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        for pattern in STOP_HEADING_PATTERNS
    ]

    nearest_stop_index: int | None = None

    for pattern in compiled_patterns:
        match = pattern.search(full_text, pos=start_position)

        if match is not None:
            if nearest_stop_index is None or match.start() < nearest_stop_index:
                nearest_stop_index = match.start()

    return nearest_stop_index if nearest_stop_index is not None else len(full_text)


def detect_reference_section(
    full_text: str,
) -> ReferenceSectionDetectionResult | None:
    if not full_text or not full_text.strip():
        return None

    reference_heading_match = _find_last_reference_heading(full_text)

    if reference_heading_match is None:
        return None

    heading = reference_heading_match.group(1).strip()
    start_index = reference_heading_match.start()
    content_start = reference_heading_match.end()

    end_index = _find_next_stop_heading(
        full_text=full_text,
        start_position=content_start,
    )

    raw_text = full_text[content_start:end_index].strip()

    if not raw_text or len(raw_text.split()) < 5:
        return None

    return ReferenceSectionDetectionResult(
        heading=heading,
        raw_text=raw_text,
        start_index=start_index,
        end_index=end_index,
        detection_method="heading_keyword",
    )