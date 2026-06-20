from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.class_model import ClassModel
from app.models.processing_job import ProcessingJob
from app.models.report import Report, ReportExport
from app.models.submission import Submission


def get_user_role(current_user: Any) -> str:
    return str(getattr(current_user, "role", "")).strip().upper()


def is_admin(current_user: Any) -> bool:
    return get_user_role(current_user) == "ADMIN"


def _actor(current_user: Any | None = None, user: Any | None = None) -> Any:
    resolved_user = current_user if current_user is not None else user
    if resolved_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "AUTH_REQUIRED",
                "message": "Authentication is required.",
                "details": None,
            },
        )
    return resolved_user


def _raise_not_found(
    resource_name: str,
    resource_id: UUID,
    error_code: str,
    message: str,
) -> None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error_code": error_code,
            "message": message,
            "details": {
                f"{resource_name}_id": str(resource_id),
            },
        },
    )


def _raise_ownership_forbidden(
    current_user: Any,
    owner_id: UUID | str | None,
    resource_name: str,
    resource_id: UUID,
) -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error_code": "AUTH_OWNERSHIP_FORBIDDEN",
            "message": "You do not have permission to access this resource.",
            "details": {
                "resource_type": resource_name,
                "resource_id": str(resource_id),
                "current_user_id": str(getattr(current_user, "id", "")),
                "owner_id": str(owner_id) if owner_id is not None else None,
            },
        },
    )


def _ensure_owner_or_admin(
    current_user: Any,
    owner_id: UUID | str | None,
    resource_name: str,
    resource_id: UUID,
) -> None:
    if is_admin(current_user):
        return

    if str(owner_id) != str(getattr(current_user, "id", "")):
        _raise_ownership_forbidden(
            current_user=current_user,
            owner_id=owner_id,
            resource_name=resource_name,
            resource_id=resource_id,
        )


def ensure_class_access_or_admin(
    db: Session,
    class_id: UUID,
    current_user: Any,
) -> ClassModel:
    classroom = db.execute(
        select(ClassModel).where(
            ClassModel.id == class_id,
            ClassModel.deleted_at.is_(None),
        )
    ).scalar_one_or_none()

    if classroom is None:
        _raise_not_found(
            resource_name="class",
            resource_id=class_id,
            error_code="CLASS_NOT_FOUND",
            message="Class not found.",
        )

    _ensure_owner_or_admin(
        current_user=current_user,
        owner_id=classroom.lecturer_id,
        resource_name="class",
        resource_id=class_id,
    )
    return classroom


def ensure_assignment_access_or_admin(
    db: Session,
    assignment_id: UUID,
    current_user: Any,
) -> Assignment:
    row = db.execute(
        select(Assignment, ClassModel)
        .join(ClassModel, Assignment.class_id == ClassModel.id)
        .where(
            Assignment.id == assignment_id,
            Assignment.deleted_at.is_(None),
            ClassModel.deleted_at.is_(None),
        )
    ).first()

    if row is None:
        _raise_not_found(
            resource_name="assignment",
            resource_id=assignment_id,
            error_code="ASSIGNMENT_NOT_FOUND",
            message="Assignment not found.",
        )

    assignment, classroom = row
    _ensure_owner_or_admin(
        current_user=current_user,
        owner_id=classroom.lecturer_id,
        resource_name="assignment",
        resource_id=assignment_id,
    )
    return assignment


def ensure_submission_access_or_admin(
    db: Session,
    submission_id: UUID,
    current_user: Any,
) -> Submission:
    row = db.execute(
        select(Submission, ClassModel)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .join(ClassModel, Assignment.class_id == ClassModel.id)
        .where(
            Submission.id == submission_id,
            Submission.deleted_at.is_(None),
            Assignment.deleted_at.is_(None),
            ClassModel.deleted_at.is_(None),
        )
    ).first()

    if row is None:
        _raise_not_found(
            resource_name="submission",
            resource_id=submission_id,
            error_code="SUBMISSION_NOT_FOUND",
            message="Submission not found.",
        )

    submission, classroom = row
    _ensure_owner_or_admin(
        current_user=current_user,
        owner_id=classroom.lecturer_id,
        resource_name="submission",
        resource_id=submission_id,
    )
    return submission


def ensure_job_access_or_admin(
    db: Session,
    job_id: UUID,
    current_user: Any,
) -> ProcessingJob:
    row = db.execute(
        select(ProcessingJob, ClassModel)
        .join(Submission, ProcessingJob.submission_id == Submission.id)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .join(ClassModel, Assignment.class_id == ClassModel.id)
        .where(ProcessingJob.id == job_id)
    ).first()

    if row is None:
        _raise_not_found(
            resource_name="job",
            resource_id=job_id,
            error_code="JOB_NOT_FOUND",
            message="Processing job not found.",
        )

    job, classroom = row
    _ensure_owner_or_admin(
        current_user=current_user,
        owner_id=classroom.lecturer_id,
        resource_name="job",
        resource_id=job_id,
    )
    return job


def get_accessible_report_or_404(
    db: Session,
    report_id: UUID,
    current_user: Any | None = None,
    user: Any | None = None,
) -> Report:
    actor = _actor(current_user=current_user, user=user)
    row = db.execute(
        select(Report, ClassModel)
        .join(Submission, Report.submission_id == Submission.id)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .join(ClassModel, Assignment.class_id == ClassModel.id)
        .where(Report.id == report_id)
    ).first()

    if row is None:
        _raise_not_found(
            resource_name="report",
            resource_id=report_id,
            error_code="REPORT_NOT_FOUND",
            message="Report not found.",
        )

    report, classroom = row
    _ensure_owner_or_admin(
        current_user=actor,
        owner_id=classroom.lecturer_id,
        resource_name="report",
        resource_id=report_id,
    )
    return report


def get_accessible_export_or_404(
    db: Session,
    export_id: UUID,
    current_user: Any | None = None,
    user: Any | None = None,
) -> ReportExport:
    actor = _actor(current_user=current_user, user=user)
    row = db.execute(
        select(ReportExport, ClassModel)
        .join(Report, ReportExport.report_id == Report.id)
        .join(Submission, Report.submission_id == Submission.id)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .join(ClassModel, Assignment.class_id == ClassModel.id)
        .where(ReportExport.id == export_id)
    ).first()

    if row is None:
        _raise_not_found(
            resource_name="export",
            resource_id=export_id,
            error_code="REPORT_EXPORT_NOT_FOUND",
            message="Report export not found.",
        )

    report_export, classroom = row
    _ensure_owner_or_admin(
        current_user=actor,
        owner_id=classroom.lecturer_id,
        resource_name="report_export",
        resource_id=export_id,
    )
    return report_export


def ensure_class_access(
    db: Session,
    class_id: UUID,
    current_user: Any,
) -> ClassModel:
    return ensure_class_access_or_admin(
        db=db,
        class_id=class_id,
        current_user=current_user,
    )


def ensure_assignment_access(
    db: Session,
    assignment_id: UUID,
    current_user: Any,
) -> Assignment:
    return ensure_assignment_access_or_admin(
        db=db,
        assignment_id=assignment_id,
        current_user=current_user,
    )


def ensure_submission_access(
    db: Session,
    submission_id: UUID,
    current_user: Any,
) -> Submission:
    return ensure_submission_access_or_admin(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
    )


def ensure_job_access(
    db: Session,
    job_id: UUID,
    current_user: Any,
) -> ProcessingJob:
    return ensure_job_access_or_admin(
        db=db,
        job_id=job_id,
        current_user=current_user,
    )


def ensure_report_access_or_admin(
    db: Session,
    report_id: UUID,
    current_user: Any,
) -> Report:
    return get_accessible_report_or_404(
        db=db,
        report_id=report_id,
        current_user=current_user,
    )


def get_accessible_submission_or_404(
    db: Session,
    submission_id: UUID,
    current_user: Any | None = None,
    user: Any | None = None,
) -> Submission:
    return ensure_submission_access_or_admin(
        db=db,
        submission_id=submission_id,
        current_user=_actor(current_user=current_user, user=user),
    )
