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


# ---------------------------------------------------------------------
# Compatibility wrappers
# Các endpoint hiện tại có thể đang import tên ngắn như ensure_class_access.
# Giữ wrapper để không phải sửa hàng loạt endpoint.
# ---------------------------------------------------------------------


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

def get_accessible_submission_or_404(
    db: Session,
    submission_id: UUID,
    current_user: Any,
) -> Submission:
    """
    Lấy submission nếu user có quyền truy cập.

    Hàm này là alias/wrapper cho report_service.
    Logic thật dùng lại ensure_submission_access_or_admin().
    """

    return ensure_submission_access_or_admin(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
    )


def get_accessible_report_or_404(
    db: Session,
    report_id: UUID,
    current_user: Any,
) -> Report:
    """
    Lấy report nếu user có quyền truy cập.

    Quyền truy cập report được suy ra theo chuỗi:

    report
    → submission
    → assignment
    → class
    → lecturer_id

    Admin được truy cập tất cả.
    Lecturer chỉ được truy cập report thuộc class mình phụ trách.
    """

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
            message="Không tìm thấy báo cáo thẩm định.",
        )

    report, classroom = row

    if is_admin(current_user):
        return report

    if str(classroom.lecturer_id) != str(getattr(current_user, "id", "")):
        _raise_ownership_forbidden(
            current_user=current_user,
            owner_id=classroom.lecturer_id,
            resource_name="report",
            resource_id=report_id,
        )

    return report


def ensure_report_access_or_admin(
    db: Session,
    report_id: UUID,
    current_user: Any,
) -> Report:
    """
    Alias tương thích nếu endpoint/service khác dùng tên ensure_*.
    """

    return get_accessible_report_or_404(
        db=db,
        report_id=report_id,
        current_user=current_user,
    )

def get_accessible_export_or_404(
    db: Session,
    export_id: UUID,
    current_user: Any,
) -> ReportExport:
    """
    Lấy report export nếu user có quyền truy cập.

    Quyền được suy ra theo chuỗi:

    report_export
    → report
    → submission
    → assignment
    → class
    → lecturer_id

    Admin được truy cập tất cả.
    Lecturer chỉ được truy cập export thuộc lớp mình phụ trách.
    """

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
            message="Không tìm thấy file export báo cáo.",
        )

    report_export, classroom = row

    if is_admin(current_user):
        return report_export

    if str(classroom.lecturer_id) != str(getattr(current_user, "id", "")):
        _raise_ownership_forbidden(
            current_user=current_user,
            owner_id=classroom.lecturer_id,
            resource_name="report_export",
            resource_id=export_id,
        )

    return report_export