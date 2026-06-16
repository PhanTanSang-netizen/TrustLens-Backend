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
    r"^\s*(tài\s+liệu\s+tham\s+khảo)\s*:?\s*$",
    r"^\s*(danh\s+mục\s+tài\s+liệu\s+tham\s+khảo)\s*:?\s*$",
    r"^\s*(references)\s*:?\s*$",
    r"^\s*(bibliography)\s*:?\s*$",
    r"^\s*(reference\s+list)\s*:?\s*$",
]


def detect_reference_section(
    full_text: str,
) -> ReferenceSectionDetectionResult | None:
    if not full_text or not full_text.strip():
        return None

    compiled_patterns = [
        re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        for pattern in REFERENCE_HEADING_PATTERNS
    ]

    best_match: re.Match[str] | None = None

    for pattern in compiled_patterns:
        for match in pattern.finditer(full_text):
            if best_match is None or match.start() > best_match.start():
                best_match = match

    if best_match is None:
        return None

    heading = best_match.group(1).strip()
    start_index = best_match.start()
    content_start = best_match.end()
    end_index = len(full_text)

    raw_text = full_text[content_start:end_index].strip()

    return ReferenceSectionDetectionResult(
        heading=heading,
        raw_text=raw_text,
        start_index=start_index,
        end_index=end_index,
        detection_method="heading_keyword",
    )