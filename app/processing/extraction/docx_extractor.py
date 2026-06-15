from dataclasses import dataclass
from pathlib import Path

from docx import Document


@dataclass
class ExtractedTextResult:
    full_text: str
    word_count: int
    page_count: int | None
    extraction_method: str


def extract_text_from_docx(file_path: str) -> ExtractedTextResult:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File không tồn tại: {file_path}")

    if path.suffix.lower() != ".docx":
        raise ValueError("File không phải DOCX.")

    document = Document(str(path))

    paragraphs: list[str] = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            paragraphs.append(text)

    for table in document.tables:
        for row in table.rows:
            row_texts: list[str] = []
            for cell in row.cells:
                cell_text = cell.text.strip()
                if cell_text:
                    row_texts.append(cell_text)

            if row_texts:
                paragraphs.append(" | ".join(row_texts))

    full_text = "\n".join(paragraphs).strip()
    word_count = len(full_text.split()) if full_text else 0

    return ExtractedTextResult(
        full_text=full_text,
        word_count=word_count,
        page_count=None,
        extraction_method="python-docx",
    )