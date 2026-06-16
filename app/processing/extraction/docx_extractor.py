from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph


@dataclass
class ExtractedTextResult:
    full_text: str
    word_count: int
    page_count: int | None
    extraction_method: str


def iter_block_items(document) -> Iterator[Paragraph | Table]:
    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def extract_table_text(table: Table) -> list[str]:
    lines: list[str] = []

    for row in table.rows:
        row_texts: list[str] = []

        for cell in row.cells:
            cell_text = cell.text.strip()

            if cell_text:
                row_texts.append(cell_text)

        if row_texts:
            lines.append(" | ".join(row_texts))

    return lines


def extract_text_from_docx(file_path: str) -> ExtractedTextResult:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File không tồn tại: {file_path}")

    if path.suffix.lower() != ".docx":
        raise ValueError("File không phải DOCX.")

    document = Document(str(path))

    blocks: list[str] = []

    for block in iter_block_items(document):
        if isinstance(block, Paragraph):
            text = block.text.strip()

            if text:
                blocks.append(text)

        elif isinstance(block, Table):
            table_lines = extract_table_text(block)

            if table_lines:
                blocks.extend(table_lines)

    full_text = "\n".join(blocks).strip()
    word_count = len(full_text.split()) if full_text else 0

    return ExtractedTextResult(
        full_text=full_text,
        word_count=word_count,
        page_count=None,
        extraction_method="python-docx",
    )