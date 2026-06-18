from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.export.docx_exporter import (
    export_report_to_docx_bytes,
    generate_docx_report_filename,
)
from app.services.report_service import get_submission_report


DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
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

    docx_content = export_report_to_docx_bytes(
        report_data=report_data,
    )

    filename = generate_docx_report_filename(
        submission_id=str(submission_id),
    )

    return ExportedReportFile(
        filename=filename,
        media_type=DOCX_MEDIA_TYPE,
        content=docx_content,
    )


# Compatibility alias
def generate_docx_export(
    db: Session,
    submission_id: UUID,
) -> ExportedReportFile:
    return export_submission_report_to_docx(
        db=db,
        submission_id=submission_id,
    )