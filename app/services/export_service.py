from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.export.docx_exporter import (
    export_report_to_docx_bytes,
    generate_docx_report_filename,
)
from app.export.pdf_exporter import (
    export_report_to_pdf_bytes,
    generate_pdf_report_filename,
)
from app.export.xlsx_exporter import (
    export_report_to_xlsx_bytes,
    generate_xlsx_report_filename,
)
from app.services.report_service import get_submission_report


DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
PDF_MEDIA_TYPE = "application/pdf"
XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


@dataclass
class ExportedReportFile:
    filename: str
    media_type: str
    content: bytes


def export_submission_report_to_docx(
    db: Session,
    submission_id: UUID,
) -> ExportedReportFile:
    report_data = get_submission_report(
        db=db,
        submission_id=submission_id,
    )

    return ExportedReportFile(
        filename=generate_docx_report_filename(str(submission_id)),
        media_type=DOCX_MEDIA_TYPE,
        content=export_report_to_docx_bytes(report_data),
    )


def export_submission_report_to_pdf(
    db: Session,
    submission_id: UUID,
) -> ExportedReportFile:
    report_data = get_submission_report(
        db=db,
        submission_id=submission_id,
    )

    return ExportedReportFile(
        filename=generate_pdf_report_filename(str(submission_id)),
        media_type=PDF_MEDIA_TYPE,
        content=export_report_to_pdf_bytes(report_data),
    )


def export_submission_report_to_xlsx(
    db: Session,
    submission_id: UUID,
) -> ExportedReportFile:
    report_data = get_submission_report(
        db=db,
        submission_id=submission_id,
    )

    return ExportedReportFile(
        filename=generate_xlsx_report_filename(str(submission_id)),
        media_type=XLSX_MEDIA_TYPE,
        content=export_report_to_xlsx_bytes(report_data),
    )


def generate_docx_export(
    db: Session,
    submission_id: UUID,
) -> ExportedReportFile:
    return export_submission_report_to_docx(
        db=db,
        submission_id=submission_id,
    )


def generate_pdf_export(
    db: Session,
    submission_id: UUID,
) -> ExportedReportFile:
    return export_submission_report_to_pdf(
        db=db,
        submission_id=submission_id,
    )


def generate_xlsx_export(
    db: Session,
    submission_id: UUID,
) -> ExportedReportFile:
    return export_submission_report_to_xlsx(
        db=db,
        submission_id=submission_id,
    )