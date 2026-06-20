from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except ModuleNotFoundError as exc:
    REPORTLAB_IMPORT_ERROR = exc
    colors = None
    TA_LEFT = 0
    A4 = (595.27, 841.89)
    ParagraphStyle = Any
    Paragraph = Any
    SimpleDocTemplate = None
    Spacer = Any
    Table = Any
    TableStyle = Any
    cm = 28.3464567
    pdfmetrics = None
    TTFont = None
else:
    REPORTLAB_IMPORT_ERROR = None


def _safe_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value)


def _register_unicode_font() -> str:
    candidate_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]

    for font_path in candidate_paths:
        path = Path(font_path)
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont("TrustLensUnicode", str(path)))
                return "TrustLensUnicode"
            except Exception:
                continue

    return "Helvetica"


def _build_styles() -> dict[str, ParagraphStyle]:
    font_name = _register_unicode_font()
    styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            name="TrustLensTitle",
            parent=styles["Title"],
            fontName=font_name,
            fontSize=18,
            leading=22,
            alignment=TA_LEFT,
            spaceAfter=14,
        ),
        "heading1": ParagraphStyle(
            name="TrustLensHeading1",
            parent=styles["Heading1"],
            fontName=font_name,
            fontSize=13,
            leading=16,
            spaceBefore=12,
            spaceAfter=8,
        ),
        "heading2": ParagraphStyle(
            name="TrustLensHeading2",
            parent=styles["Heading2"],
            fontName=font_name,
            fontSize=11,
            leading=14,
            spaceBefore=8,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            name="TrustLensBody",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=9,
            leading=12,
            spaceAfter=5,
        ),
        "small": ParagraphStyle(
            name="TrustLensSmall",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=8,
            leading=10,
        ),
    }


def _paragraph(value: Any, style: ParagraphStyle) -> Paragraph:
    text = _safe_text(value)
    text = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )
    return Paragraph(text, style)


def _add_key_value_table(
    story: list[Any],
    data: dict[str, Any],
    styles: dict[str, ParagraphStyle],
) -> None:
    rows = []

    for key, value in data.items():
        rows.append([
            _paragraph(key, styles["small"]),
            _paragraph(value, styles["small"]),
        ])

    if not rows:
        return

    table = Table(rows, colWidths=[5.0 * cm, 11.5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 0.25 * cm))


def _add_submission_info(
    story: list[Any],
    report_data: dict[str, Any],
    styles: dict[str, ParagraphStyle],
) -> None:
    story.append(_paragraph("1. Thông tin bài nộp", styles["heading1"]))

    submission = report_data.get("submission") or {}
    file_info = report_data.get("file") or {}

    _add_key_value_table(
        story=story,
        data={
            "Submission ID": submission.get("id"),
            "Assignment ID": submission.get("assignment_id"),
            "Owner Label": submission.get("owner_label"),
            "Submission Status": submission.get("status"),
            "Overall Score": submission.get("overall_score"),
            "Created At": submission.get("created_at"),
            "File Name": file_info.get("original_name"),
            "File Type": file_info.get("mime_type"),
            "File Size Bytes": file_info.get("size_bytes"),
        },
        styles=styles,
    )


def _add_summary(
    story: list[Any],
    report_data: dict[str, Any],
    styles: dict[str, ParagraphStyle],
) -> None:
    story.append(_paragraph("2. Tóm tắt xử lý", styles["heading1"]))

    summary = report_data.get("summary") or {}
    processing = summary.get("processing") or {}
    verification = summary.get("verification") or {}
    score = summary.get("score") or {}

    story.append(_paragraph("2.1. Pipeline", styles["heading2"]))
    _add_key_value_table(
        story=story,
        data={
            "Submission Status": processing.get("submission_status"),
            "Has Extracted Text": processing.get("has_extracted_text"),
            "Has Reference Section": processing.get("has_reference_section"),
            "Citation Count": processing.get("citation_count"),
            "Metadata Record Count": processing.get("metadata_record_count"),
        },
        styles=styles,
    )

    story.append(_paragraph("2.2. Metadata Verification", styles["heading2"]))
    _add_key_value_table(
        story=story,
        data={
            "Total": verification.get("total"),
            "Verified": verification.get("verified"),
            "Basic Metadata Present": verification.get("basic_metadata_present"),
            "Broken": verification.get("broken"),
            "Forbidden": verification.get("forbidden"),
            "Unreachable": verification.get("unreachable"),
            "Not Provided": verification.get("not_provided"),
        },
        styles=styles,
    )

    story.append(_paragraph("2.3. Trust Score", styles["heading2"]))
    _add_key_value_table(
        story=story,
        data={
            "Overall Score": score.get("overall_score"),
            "Trust Level": score.get("trust_level"),
            "Note": score.get("note"),
        },
        styles=styles,
    )


def _add_reference_section(
    story: list[Any],
    report_data: dict[str, Any],
    styles: dict[str, ParagraphStyle],
) -> None:
    story.append(_paragraph("3. Phần tài liệu tham khảo được nhận diện", styles["heading1"]))

    reference_section = report_data.get("reference_section")

    if not reference_section:
        story.append(_paragraph("Chưa nhận diện được phần tài liệu tham khảo.", styles["body"]))
        return

    _add_key_value_table(
        story=story,
        data={
            "Heading": reference_section.get("heading"),
            "Start Index": reference_section.get("start_index"),
            "End Index": reference_section.get("end_index"),
            "Detection Method": reference_section.get("detection_method"),
        },
        styles=styles,
    )

    preview = reference_section.get("raw_text_preview")
    if preview:
        story.append(_paragraph("Preview:", styles["heading2"]))
        story.append(_paragraph(preview, styles["small"]))


def _add_citations(
    story: list[Any],
    report_data: dict[str, Any],
    styles: dict[str, ParagraphStyle],
) -> None:
    story.append(_paragraph("4. Danh sách citation", styles["heading1"]))

    citations = report_data.get("citations") or []

    if not citations:
        story.append(_paragraph("Chưa có citation được tách.", styles["body"]))
        return

    for item in citations:
        citation = item.get("citation") or {}
        metadata = item.get("metadata") or {}
        warnings = item.get("warnings") or []

        sequence_no = citation.get("sequence_no") or ""
        title = citation.get("title") or "Không có tiêu đề"

        story.append(_paragraph(f"4.{sequence_no}. {title}", styles["heading2"]))
        story.append(_paragraph("Citation gốc:", styles["small"]))
        story.append(_paragraph(citation.get("raw_text"), styles["small"]))

        _add_key_value_table(
            story=story,
            data={
                "Detected Style": citation.get("detected_style"),
                "Authors": citation.get("authors"),
                "Title": citation.get("title"),
                "Year": citation.get("year"),
                "DOI": citation.get("doi"),
                "URL": citation.get("url"),
                "Verification Status": metadata.get("verification_status"),
                "Provider": metadata.get("provider"),
                "Confidence Score": metadata.get("confidence_score"),
                "Source URL": metadata.get("source_url"),
                "Trust Level": item.get("trust_level"),
                "Score": item.get("score"),
                "Warnings": ", ".join(warnings) if warnings else "Không có",
            },
            styles=styles,
        )


def build_pdf_report_bytes(
    report_data: dict[str, Any],
) -> bytes:
    if REPORTLAB_IMPORT_ERROR is not None:
        raise RuntimeError("reportlab is required to export PDF reports.") from REPORTLAB_IMPORT_ERROR

    buffer = BytesIO()
    styles = _build_styles()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    story: list[Any] = []

    story.append(_paragraph("TrustLens - Báo cáo thẩm định tài liệu tham khảo", styles["title"]))

    message = report_data.get("message")
    if message:
        story.append(_paragraph(message, styles["body"]))

    _add_submission_info(story, report_data, styles)
    _add_summary(story, report_data, styles)
    _add_reference_section(story, report_data, styles)
    _add_citations(story, report_data, styles)

    document.build(story)

    buffer.seek(0)
    return buffer.read()


def export_report_to_pdf_bytes(
    report_data: dict[str, Any],
) -> bytes:
    return build_pdf_report_bytes(report_data)


def export_report_to_pdf_file(
    report_data: dict[str, Any],
    output_path: str | Path,
) -> str:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(build_pdf_report_bytes(report_data))
    return str(output_path)


def generate_pdf_report_filename(
    submission_id: str,
) -> str:
    return f"trustlens_report_{submission_id}_{uuid4().hex[:8]}.pdf"