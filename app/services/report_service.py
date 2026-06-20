from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.processing_job import ProcessingJob
from app.models.report import Report
from app.core.trust_score_definition import build_trust_score_definition
from app.services.access_control_service import (
    get_accessible_report_or_404,
    get_accessible_submission_or_404,
)
from app.services.analysis_pipeline_service import run_analysis_pipeline
from app.services.job_service import create_queued_job


ACTIVE_REPORT_JOB_STATUSES = {
    "QUEUED",
    "VALIDATING",
    "EXTRACTING",
    "DETECTING_REFERENCES",
    "PARSING_CITATIONS",
    "NORMALIZING",
    "VERIFYING_METADATA",
    "SCORING",
    "BUILDING_REPORT",
}


def serialize_report(report: Report) -> dict:
    submission = getattr(report, "submission", None)
    owner_label = getattr(submission, "owner_label", None)

    return {
        "report_id": report.id,
        "submission_id": report.submission_id,
        "owner_label": owner_label,
        "student_name": owner_label,
        "job_id": report.job_id,
        "scoring_config_version": report.scoring_config_version,
        "scoring_preset_name": report.scoring_config_version,
        "scoring_preset_code": report.scoring_config_version,
        "scoring_preset_version": 1,
        "trust_score": build_trust_score_definition(version=report.scoring_config_version),
        "revision_number": 1,
        "report_trust_score": report.report_trust_score or 0,
        "confidence_score": report.confidence_score or 0,
        "overall_label": report.overall_label or "needs_review",
        "summary": report.summary or {},
        "report_penalty": {"total": report.report_penalty or 0, "items": []},
        "component_summary": report.component_summary or {},
        "citations": report.citations_payload or [],
        "warnings": report.warnings or [],
        "created_at": report.created_at,
    }


def _latest_report_by_submission_id(
    db: Session,
    submission_id: UUID,
) -> Report | None:
    return db.execute(
        select(Report)
        .where(Report.submission_id == submission_id)
        .order_by(Report.created_at.desc())
    ).scalars().first()


def _latest_job_by_submission_id(
    db: Session,
    submission_id: UUID,
) -> ProcessingJob | None:
    return db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.submission_id == submission_id)
        .order_by(ProcessingJob.created_at.desc())
    ).scalars().first()


def _raise_report_not_ready(
    submission_id: UUID,
    job: ProcessingJob | None,
) -> None:
    details = {"submission_id": str(submission_id)}
    if job is not None:
        details.update({
            "job_id": str(job.id),
            "job_status": job.status,
            "job_step": job.step,
            "error_code": job.error_code,
            "error_message": job.error_message,
        })

    status_code = (
        status.HTTP_422_UNPROCESSABLE_ENTITY
        if job is not None and str(job.status).startswith("FAILED")
        else status.HTTP_409_CONFLICT
    )

    raise HTTPException(
        status_code=status_code,
        detail={
            "error_code": "REPORT_NOT_READY",
            "message": "Report is not available yet. Run the analysis pipeline first.",
            "details": details,
        },
    )


def _ensure_report_for_submission(
    db: Session,
    submission_id: UUID,
    current_user,
) -> Report:
    report = _latest_report_by_submission_id(
        db=db,
        submission_id=submission_id,
    )
    if report is not None:
        return report

    latest_job = _latest_job_by_submission_id(
        db=db,
        submission_id=submission_id,
    )
    if latest_job is not None and latest_job.status in ACTIVE_REPORT_JOB_STATUSES:
        _raise_report_not_ready(
            submission_id=submission_id,
            job=latest_job,
        )

    job = create_queued_job(
        db=db,
        submission_id=submission_id,
        created_by=getattr(current_user, "id", None),
    )

    run_analysis_pipeline(str(job.id))
    db.expire_all()

    report = _latest_report_by_submission_id(
        db=db,
        submission_id=submission_id,
    )
    if report is None:
        failed_job = _latest_job_by_submission_id(
            db=db,
            submission_id=submission_id,
        )
        _raise_report_not_ready(
            submission_id=submission_id,
            job=failed_job,
        )

    return report


def resolve_submission_id_for_report_route(
    db: Session,
    submission_or_report_id: UUID,
    current_user,
) -> UUID:
    try:
        submission = get_accessible_submission_or_404(
            db=db,
            submission_id=submission_or_report_id,
            user=current_user,
        )
        return submission.id
    except HTTPException as exc:
        if exc.status_code != status.HTTP_404_NOT_FOUND:
            raise

    report = get_accessible_report_or_404(
        db=db,
        report_id=submission_or_report_id,
        user=current_user,
    )
    return report.submission_id


def get_report(db: Session, report_id: UUID, current_user) -> dict:
    return serialize_report(
        get_accessible_report_or_404(
            db=db,
            report_id=report_id,
            user=current_user,
        )
    )


def get_report_by_submission(
    db: Session,
    submission_id: UUID,
    current_user,
) -> dict:
    try:
        submission = get_accessible_submission_or_404(
            db=db,
            submission_id=submission_id,
            user=current_user,
        )
    except HTTPException as exc:
        if exc.status_code != status.HTTP_404_NOT_FOUND:
            raise
        return get_report(
            db=db,
            report_id=submission_id,
            current_user=current_user,
        )

    report = _ensure_report_for_submission(
        db=db,
        submission_id=submission.id,
        current_user=current_user,
    )
    return serialize_report(report)


def get_report_history(db: Session, report_id: UUID, current_user) -> list[dict]:
    report = get_accessible_report_or_404(
        db=db,
        report_id=report_id,
        user=current_user,
    )
    return [
        {
            "id": report.id,
            "revision_number": 1,
            "report_trust_score": report.report_trust_score or 0,
            "created_at": report.created_at,
        }
    ]


def get_submission_report(
    db,
    submission_id,
    current_user=None,
):
    return get_report_by_submission(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
    )
