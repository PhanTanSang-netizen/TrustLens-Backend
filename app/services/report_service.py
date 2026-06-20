from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.report import Report
from app.services.access_control_service import get_accessible_report_or_404, get_accessible_submission_or_404


def serialize_report(report: Report) -> dict:
    return {
        "report_id": report.id,
        "submission_id": report.submission_id,
        "job_id": report.job_id,
        "scoring_config_version": report.scoring_config_version,
        "scoring_preset_name": "Default Trust Score",
        "scoring_preset_code": "IT_GENERAL",
        "scoring_preset_version": 1,
        "revision_number": 1,
        "report_trust_score": report.report_trust_score,
        "confidence_score": report.confidence_score,
        "overall_label": report.overall_label,
        "summary": report.summary,
        "report_penalty": {"total": report.report_penalty, "items": []},
        "component_summary": report.component_summary,
        "citations": report.citations_payload,
        "warnings": report.warnings,
        "created_at": report.created_at,
    }


def get_report(db: Session, report_id: UUID, current_user) -> dict:
    return serialize_report(get_accessible_report_or_404(db=db, report_id=report_id, user=current_user))


def get_report_by_submission(db: Session, submission_id: UUID, current_user) -> dict:
    get_accessible_submission_or_404(db=db, submission_id=submission_id, user=current_user)
    report = db.execute(select(Report).where(Report.submission_id == submission_id)).scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error_code": "REPORT_NOT_FOUND", "message": "Report is not available.", "details": {"submission_id": str(submission_id)}})
    return serialize_report(report)


def get_report_history(db: Session, report_id: UUID, current_user) -> list[dict]:
    report = get_accessible_report_or_404(db=db, report_id=report_id, user=current_user)
    return [{"id": report.id, "revision_number": 1, "report_trust_score": report.report_trust_score, "created_at": report.created_at}]

def get_submission_report(
    db,
    submission_id,
    current_user=None,
):
    """
    Lấy report mới nhất của một submission.

    Hàm này được app/api/v1/endpoints/reports.py import.
    """

    from fastapi import HTTPException, status
    from sqlalchemy import select

    from app.models.report import Report
    from app.services.access_control_service import get_accessible_submission_or_404

    if current_user is not None:
        get_accessible_submission_or_404(
            db=db,
            submission_id=submission_id,
            current_user=current_user,
        )

    report = db.execute(
        select(Report)
        .where(Report.submission_id == submission_id)
        .order_by(Report.created_at.desc())
    ).scalars().first()

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "REPORT_NOT_FOUND",
                "message": "Không tìm thấy report của bài nộp này.",
                "details": {
                    "submission_id": str(submission_id),
                },
            },
        )

    return report
