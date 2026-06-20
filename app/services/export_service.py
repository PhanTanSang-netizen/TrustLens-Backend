from pathlib import Path
from textwrap import wrap
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.report import Report, ReportExport
from app.services.audit_service import record_audit_log
from app.services.report_service import serialize_report


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_minimal_pdf(lines: list[str]) -> bytes:
    stream_lines = ["BT", "/F1 10 Tf", "50 790 Td", "14 TL"]
    for line in lines[:52]:
        stream_lines.extend([f"({_escape_pdf_text(line[:110])}) Tj", "T*"])
    stream_lines.append("ET")
    stream = "\n".join(stream_lines).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii") + b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(f"trailer\n<< /Root 1 0 R /Size {len(objects) + 1} >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii"))
    return bytes(pdf)


def create_report_export(db: Session, report: Report, export_format: str, include_raw_citation: bool, created_by: UUID | None) -> ReportExport:
    if export_format.lower() != "pdf":
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail={"error_code": "EXPORT_FORMAT_NOT_IMPLEMENTED", "message": "Only PDF export is implemented in P0.", "details": {"format": export_format}})
    payload = serialize_report(report)
    lines = [
        "TrustLens Academic Reference Report",
        f"Report ID: {report.id}",
        f"Submission ID: {report.submission_id}",
        f"Trust Score: {report.report_trust_score}/100",
        f"Confidence: {round(report.confidence_score * 100)}%",
        f"Label: {report.overall_label}",
        f"Scoring config: {report.scoring_config_version}",
        "",
        "Component summary:",
    ]
    for key, value in report.component_summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "Citation details:"])
    for index, citation in enumerate(payload["citations"], start=1):
        raw = citation.get("raw_text") if include_raw_citation else citation.get("normalized_fields", {}).get("title")
        score = citation.get("scores", {}).get("reference_trust_score", 0)
        lines.extend(wrap(f"{index}. [{score}/100] {raw}", width=100))
    lines.append("Disclaimer: TrustLens supports academic review and does not replace lecturer judgement.")
    export_dir = Path(settings.UPLOAD_DIR) / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    report_export = ReportExport(report_id=report.id, format="pdf", storage_path="", status="completed", created_by=created_by)
    db.add(report_export)
    db.flush()
    export_path = export_dir / f"{report_export.id}.pdf"
    export_path.write_bytes(_build_minimal_pdf(lines))
    report_export.storage_path = str(export_path)
    record_audit_log(db=db, user_id=created_by, action="EXPORT_REPORT", resource_type="report", resource_id=str(report.id), message="Report PDF exported.", details={"export_id": str(report_export.id), "format": "pdf"})
    db.commit()
    db.refresh(report_export)
    return report_export
