from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.job_schema import (
    JobProcessResponse,
    JobStatusResponse,
    LatestJobResponse,
)
from app.services.access_control_service import (
    get_accessible_job_or_404,
    get_accessible_submission_or_404,
)
from app.services.analysis_pipeline_service import run_analysis_pipeline
from app.services.job_service import (
    get_latest_job_by_submission_id,
    retry_submission_processing_job,
    run_submission_processing_pipeline,
)


router = APIRouter()


def _enqueue_pipeline_if_needed(background_tasks: BackgroundTasks, job) -> None:
    if job.status == "QUEUED" and job.started_at is None:
        background_tasks.add_task(run_analysis_pipeline, str(job.id))


@router.get("/{job_id}", response_model=JobStatusResponse)
def read_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return get_accessible_job_or_404(
        db=db,
        job_id=job_id,
        user=current_user,
    )


@router.get(
    "/submissions/{submission_id}/latest",
    response_model=LatestJobResponse,
)
def read_latest_submission_job(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    get_accessible_submission_or_404(
        db=db,
        submission_id=submission_id,
        user=current_user,
    )
    job = get_latest_job_by_submission_id(
        db=db,
        submission_id=submission_id,
    )

    return {
        "message": "Latest submission job fetched successfully.",
        "submission_id": submission_id,
        "job": job,
    }


@router.post(
    "/submissions/{submission_id}/process",
    response_model=JobProcessResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def process_submission_pipeline(
    submission_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    get_accessible_submission_or_404(
        db=db,
        submission_id=submission_id,
        user=current_user,
    )
    job = run_submission_processing_pipeline(
        db=db,
        submission_id=submission_id,
        created_by=current_user.id,
    )
    _enqueue_pipeline_if_needed(background_tasks, job)
    return job


@router.post(
    "/{job_id}/retry",
    response_model=JobProcessResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_job(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    get_accessible_job_or_404(
        db=db,
        job_id=job_id,
        user=current_user,
    )
    job = retry_submission_processing_job(
        db=db,
        job_id=job_id,
        created_by=current_user.id,
    )
    _enqueue_pipeline_if_needed(background_tasks, job)
    return job
