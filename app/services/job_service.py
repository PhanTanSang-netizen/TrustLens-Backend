from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.processing_job import ProcessingJob
from app.models.report import Report
from app.models.submission import Submission


ACTIVE_JOB_STATUSES = {
    "QUEUED",
    "VALIDATING",
    "EXTRACTING",
    "PARSING",
    "VERIFYING",
    "SCORING",
    # Các trạng thái chi tiết cũ, giữ để không phá logic hiện tại
    "DETECTING_REFERENCES",
    "PARSING_CITATIONS",
    "NORMALIZING",
    "VERIFYING_METADATA",
    "BUILDING_REPORT",
}

NON_RETRYABLE_ERROR_PREFIXES = (
    "FILE_",
    "PDF_",
    "NO_REFERENCE",
    "UNSUPPORTED_FILE_TYPE",
)


def _model_has_field(field_name: str) -> bool:
    """
    Kiểm tra ProcessingJob model có field hay không.

    Lý do:
    Một số endpoint/schema cũ đang dùng current_step, report_id,
    retry_of_job_id, created_by, error_details.
    Nhưng model hiện tại có thể chưa có đủ các field này.
    Hàm này giúp service không bị TypeError khi tạo job.
    """

    return hasattr(ProcessingJob, field_name)


def get_job_by_id(
    db: Session,
    job_id: UUID,
) -> ProcessingJob | None:
    return db.execute(
        select(ProcessingJob).where(ProcessingJob.id == job_id)
    ).scalar_one_or_none()


def get_job_status(
    db: Session,
    job_id: UUID,
) -> ProcessingJob | None:
    return get_job_by_id(db=db, job_id=job_id)


def get_active_job_for_submission(
    db: Session,
    submission_id: UUID,
) -> ProcessingJob | None:
    return db.execute(
        select(ProcessingJob)
        .where(
            ProcessingJob.submission_id == submission_id,
            ProcessingJob.status.in_(ACTIVE_JOB_STATUSES),
        )
        .order_by(ProcessingJob.created_at.desc())
    ).scalars().first()


def get_latest_job_by_submission_id(
    db: Session,
    submission_id: UUID,
) -> ProcessingJob | None:
    return db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.submission_id == submission_id)
        .order_by(ProcessingJob.created_at.desc())
    ).scalar_one_or_none()


def get_report_by_submission_id(
    db: Session,
    submission_id: UUID,
) -> Report | None:
    return db.execute(
        select(Report).where(Report.submission_id == submission_id)
    ).scalar_one_or_none()


def create_queued_job(
    db: Session,
    submission_id: UUID,
    created_by: UUID | None = None,
    retry_of_job_id: UUID | None = None,
) -> ProcessingJob:
    """
    Tạo job mới ở trạng thái QUEUED.

    Dùng khi:
    - upload tạo job đầu tiên
    - analyze submission
    - retry job
    """

    job_data: dict[str, Any] = {
        "submission_id": submission_id,
        "status": "QUEUED",
        "progress": 0,
        "step": "queued",
    }

    if _model_has_field("current_step"):
        job_data["current_step"] = "queued"

    if _model_has_field("created_by"):
        job_data["created_by"] = created_by

    if _model_has_field("retry_of_job_id"):
        job_data["retry_of_job_id"] = retry_of_job_id

    if _model_has_field("parent_job_id"):
        job_data["parent_job_id"] = retry_of_job_id

    if _model_has_field("error_code"):
        job_data["error_code"] = None

    if _model_has_field("error_message"):
        job_data["error_message"] = None

    if _model_has_field("error_details"):
        job_data["error_details"] = None

    if _model_has_field("retry_count"):
        job_data["retry_count"] = 0

    job = ProcessingJob(**job_data)

    db.add(job)
    db.flush()

    submission = db.execute(
        select(Submission).where(Submission.id == submission_id)
    ).scalar_one_or_none()

    if submission is not None:
        submission.status = "QUEUED"

        if hasattr(submission, "latest_job_id"):
            submission.latest_job_id = job.id

    db.commit()
    db.refresh(job)

    return job


def retry_submission_processing_job(
    db: Session,
    job_id: UUID | None = None,
    current_user: Any | None = None,
    job: ProcessingJob | None = None,
    submission_id: UUID | None = None,
) -> ProcessingJob:
    """
    Tạo job retry cho một submission.

    Hỗ trợ nhiều kiểu gọi từ endpoint:
    - retry_submission_processing_job(db=db, job_id=job_id)
    - retry_submission_processing_job(db=db, job=old_job)
    - retry_submission_processing_job(db=db, submission_id=submission_id)

    current_user chỉ dùng để lấy created_by nếu model có field này.
    Quyền truy cập nên được kiểm trước ở access_control_service.
    """

    old_job: ProcessingJob | None = job

    if old_job is None and job_id is not None:
        old_job = get_job_by_id(db=db, job_id=job_id)

    if old_job is None and submission_id is not None:
        old_job = get_latest_job_by_submission_id(
            db=db,
            submission_id=submission_id,
        )

    if old_job is None and job_id is None and submission_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "JOB_RETRY_TARGET_REQUIRED",
                "message": "Cần cung cấp job_id hoặc submission_id để retry.",
                "details": {},
            },
        )

    if old_job is None and job_id is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "JOB_NOT_FOUND",
                "message": "Không tìm thấy job xử lý để retry.",
                "details": {
                    "job_id": str(job_id),
                },
            },
        )

    target_submission_id = (
        old_job.submission_id
        if old_job is not None
        else submission_id
    )

    if target_submission_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "JOB_RETRY_INVALID_TARGET",
                "message": "Không xác định được submission cần retry.",
                "details": {},
            },
        )

    created_by = getattr(current_user, "id", None) if current_user is not None else None
    retry_of_job_id = old_job.id if old_job is not None else None

    new_job = create_queued_job(
        db=db,
        submission_id=target_submission_id,
        created_by=created_by,
        retry_of_job_id=retry_of_job_id,
    )

    if _model_has_field("retry_count"):
        old_retry_count = getattr(old_job, "retry_count", 0) if old_job is not None else 0
        new_job.retry_count = (old_retry_count or 0) + 1
        db.commit()
        db.refresh(new_job)

    return new_job


def mark_job_running(
    db: Session,
    job: ProcessingJob,
    step: str,
    progress: int,
    status_value: str,
) -> ProcessingJob:
    job.status = status_value
    job.step = step
    job.progress = progress

    if _model_has_field("current_step"):
        job.current_step = step

    db.commit()
    db.refresh(job)

    return job


def mark_job_failed(
    db: Session,
    job: ProcessingJob,
    error_code: str,
    error_message: str,
    error_details: dict | None = None,
) -> ProcessingJob:
    job.status = "FAILED"
    job.step = "failed"

    if hasattr(job, "progress"):
        job.progress = 100

    if _model_has_field("error_code"):
        job.error_code = error_code

    if _model_has_field("error_message"):
        job.error_message = error_message

    if _model_has_field("error_details"):
        job.error_details = error_details

    db.commit()
    db.refresh(job)

    return job


def mark_job_completed(
    db: Session,
    job: ProcessingJob,
    report_id: UUID | None = None,
) -> ProcessingJob:
    job.status = "COMPLETED"
    job.step = "completed"
    job.progress = 100

    if _model_has_field("current_step"):
        job.current_step = "completed"

    if _model_has_field("report_id"):
        job.report_id = report_id

    db.commit()
    db.refresh(job)

    return job

def run_submission_processing_pipeline(
    job_id: UUID,
) -> None:
    """
    Pipeline xử lý submission ở mức MVP placeholder.

    Hàm này chạy bằng BackgroundTasks nên tự mở DB session riêng.
    Sau này thay phần cập nhật trạng thái bằng:
    - validate file
    - extract text
    - detect reference section
    - parse citation
    - metadata lookup
    - scoring
    - report
    """

    from app.db.session import SessionLocal

    db = SessionLocal()

    try:
        job = get_job_by_id(db=db, job_id=job_id)

        if job is None:
            return

        mark_job_running(
            db=db,
            job=job,
            step="validating",
            progress=10,
            status_value="VALIDATING",
        )

        mark_job_running(
            db=db,
            job=job,
            step="extracting",
            progress=30,
            status_value="EXTRACTING",
        )

        mark_job_running(
            db=db,
            job=job,
            step="parsing",
            progress=50,
            status_value="PARSING",
        )

        mark_job_running(
            db=db,
            job=job,
            step="verifying",
            progress=70,
            status_value="VERIFYING",
        )

        mark_job_running(
            db=db,
            job=job,
            step="scoring",
            progress=90,
            status_value="SCORING",
        )

        mark_job_completed(
            db=db,
            job=job,
        )

        submission = db.execute(
            select(Submission).where(Submission.id == job.submission_id)
        ).scalar_one_or_none()

        if submission is not None:
            submission.status = "COMPLETED"

            if hasattr(submission, "latest_job_id"):
                submission.latest_job_id = job.id

            db.commit()

    except Exception as exc:
        db.rollback()

        failed_job = get_job_by_id(db=db, job_id=job_id)

        if failed_job is not None:
            mark_job_failed(
                db=db,
                job=failed_job,
                error_code="PIPELINE_ERROR",
                error_message=str(exc),
            )

    finally:
        db.close()
