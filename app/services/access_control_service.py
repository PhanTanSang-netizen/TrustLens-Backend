from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.assignment import Assignment
from app.models.class_model import ClassModel
from app.models.processing_job import ProcessingJob
from app.models.report import Report, ReportExport
from app.models.submission import Submission


def _is_admin(user) -> bool:
    return getattr(user, "role", None) == "admin"


def _forbidden():
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error_code": "FORBIDDEN_RESOURCE", "message": "Forbidden resource.", "details": None},
    )


def ensure_class_access(user, classroom: ClassModel) -> None:
    if _is_admin(user):
        return
    if getattr(user, "role", None) != "lecturer" or classroom.lecturer_id != user.id:
        _forbidden()


def ensure_assignment_access(user, assignment: Assignment) -> None:
    if assignment.classroom is None:
        _forbidden()
    ensure_class_access(user, assignment.classroom)


def get_accessible_submission_or_404(db: Session, submission_id: UUID, user) -> Submission:
    submission = db.execute(
        select(Submission)
        .options(joinedload(Submission.assignment).joinedload(Assignment.classroom))
        .where(Submission.id == submission_id)
    ).scalar_one_or_none()
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "SUBMISSION_NOT_FOUND", "message": "Submission not found.", "details": {"submission_id": str(submission_id)}},
        )
    ensure_assignment_access(user, submission.assignment)
    return submission


def get_accessible_job_or_404(db: Session, job_id: UUID, user) -> ProcessingJob:
    job = db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id)).scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "JOB_NOT_FOUND", "message": "Job not found.", "details": {"job_id": str(job_id)}},
        )
    get_accessible_submission_or_404(db=db, submission_id=job.submission_id, user=user)
    return job


def get_accessible_report_or_404(db: Session, report_id: UUID, user) -> Report:
    report = db.execute(select(Report).where(Report.id == report_id)).scalar_one_or_none()
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "REPORT_NOT_FOUND", "message": "Report not found.", "details": {"report_id": str(report_id)}},
        )
    get_accessible_submission_or_404(db=db, submission_id=report.submission_id, user=user)
    return report


def get_accessible_export_or_404(db: Session, export_id: UUID, user) -> ReportExport:
    report_export = db.execute(select(ReportExport).where(ReportExport.id == export_id)).scalar_one_or_none()
    if report_export is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "EXPORT_NOT_FOUND", "message": "Export not found.", "details": {"export_id": str(export_id)}},
        )
    get_accessible_report_or_404(db=db, report_id=report_export.report_id, user=user)
    return report_export
