from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_lecturer_or_admin
from app.db.session import get_db
from app.schemas.job_schema import (
    JobProcessResponse,
    JobRead,
    LatestJobResponse,
)
from app.services.access_control_service import ensure_job_access_or_admin
from app.services.job_service import (
    create_queued_job,
    get_latest_job_by_submission_id,
    retry_submission_processing_job,
    run_submission_processing_pipeline,
)


router = APIRouter()


@router.get("/{job_id}", response_model=JobRead)
def read_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_lecturer_or_admin),
):
    return ensure_job_access_or_admin(
        db=db,
        job_id=job_id,
        current_user=current_user,
    )


@router.get(
    "/submissions/{submission_id}/latest",
    response_model=LatestJobResponse,
)
def read_latest_submission_job(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_lecturer_or_admin),
):
    job = get_latest_job_by_submission_id(
        db=db,
        submission_id=submission_id,
    )

    if job is None:
        return {
            "found": False,
            "submission_id": submission_id,
            "message": "Không tìm thấy job xử lý cho bài nộp này.",
        }

    return job


@router.post(
    "/submissions/{submission_id}/process",
    response_model=JobProcessResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def process_submission_pipeline(
    submission_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_lecturer_or_admin),
):
    ensure_submission_access_or_admin(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
    )

    job = create_queued_job(
        db=db,
        submission_id=submission_id,
        created_by=getattr(current_user, "id", None),
    )

    background_tasks.add_task(
        run_submission_processing_pipeline,
        job_id=job.id,
    )

    return {
        "job_id": job.id,
        "submission_id": job.submission_id,
        "status": job.status,
        "progress": job.progress,
        "step": job.step,
        "message": "Processing job accepted.",
    }


@router.get(
    "/{job_id}",
    response_model=JobRead,
)
def read_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_lecturer_or_admin),
):
    return ensure_job_access_or_admin(
        db=db,
        job_id=job_id,
        current_user=current_user,
    )


@router.post(
    "/{job_id}/retry",
    response_model=JobProcessResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_job(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_lecturer_or_admin),
):
    ensure_job_access_or_admin(
        db=db,
        job_id=job_id,
        current_user=current_user,
    )

    job = retry_submission_processing_job(
        db=db,
        job_id=job_id,
        current_user=current_user,
    )

    background_tasks.add_task(
        run_submission_processing_pipeline,
        job_id=job.id,
    )

    return {
        "job_id": job.id,
        "submission_id": job.submission_id,
        "status": job.status,
        "progress": job.progress,
        "step": job.step,
        "message": "Retry job accepted.",
    }