from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass
class ExtractedPdfResult:
    full_text: str
    word_count: int
    page_count: int | None
    extraction_method: str


def extract_text_from_pdf(file_path: str) -> ExtractedPdfResult:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File không tồn tại: {file_path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("File không phải PDF.")

    document = fitz.open(str(path))

    page_texts: list[str] = []

    for page in document:
        text = page.get_text("text").strip()
        if text:
            page_texts.append(text)

    page_count = document.page_count
    document.close()

    full_text = "\n\n".join(page_texts).strip()
    word_count = len(full_text.split()) if full_text else 0

    return ExtractedPdfResult(
        full_text=full_text,
        word_count=word_count,
        page_count=page_count,
        extraction_method="pymupdf",
    )