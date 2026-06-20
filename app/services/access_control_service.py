from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.assignment import Assignment
from app.models.class_model import ClassModel
from app.models.processing_job import ProcessingJob
from app.models.submission import Submission


def get_user_role(current_user: Any) -> str:
    return str(getattr(current_user, "role", "")).strip().upper()


def is_admin(current_user: Any) -> bool:
    return get_user_role(current_user) == "ADMIN"


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
            "message": "Bạn không có quyền truy cập tài nguyên không thuộc phạm vi của mình.",
            "details": {
                "resource_type": resource_name,
                "resource_id": str(resource_id),
                "current_user_id": str(getattr(current_user, "id", "")),
                "owner_id": str(owner_id) if owner_id is not None else None,
            },
        },
    )


def ensure_class_access_or_admin(
    db: Session,
    class_id: UUID,
    current_user: Any,
) -> ClassModel:
    classroom = db.execute(
        select(ClassModel).where(ClassModel.id == class_id)
    ).scalar_one_or_none()

    if classroom is None:
        _raise_not_found(
            resource_name="class",
            resource_id=class_id,
            error_code="CLASS_NOT_FOUND",
            message="Không tìm thấy lớp học phần.",
        )

    if is_admin(current_user):
        return classroom

    if str(classroom.lecturer_id) != str(getattr(current_user, "id", "")):
        _raise_ownership_forbidden(
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
        .where(Assignment.id == assignment_id)
    ).first()

    if row is None:
        _raise_not_found(
            resource_name="assignment",
            resource_id=assignment_id,
            error_code="ASSIGNMENT_NOT_FOUND",
            message="Không tìm thấy assignment cần thẩm định.",
        )

    assignment, classroom = row

    if is_admin(current_user):
        return assignment

    if str(classroom.lecturer_id) != str(getattr(current_user, "id", "")):
        _raise_ownership_forbidden(
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
        .where(Submission.id == submission_id)
    ).first()

    if row is None:
        _raise_not_found(
            resource_name="submission",
            resource_id=submission_id,
            error_code="SUBMISSION_NOT_FOUND",
            message="Không tìm thấy bài nộp.",
        )

    submission, classroom = row

    if is_admin(current_user):
        return submission

    if str(classroom.lecturer_id) != str(getattr(current_user, "id", "")):
        _raise_ownership_forbidden(
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
            message="Không tìm thấy job xử lý.",
        )

    job, classroom = row

    if is_admin(current_user):
        return job

    if str(classroom.lecturer_id) != str(getattr(current_user, "id", "")):
        _raise_ownership_forbidden(
            current_user=current_user,
            owner_id=classroom.lecturer_id,
            resource_name="job",
            resource_id=job_id,
        )

    return job
