from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
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
    current_user=Depends(get_current_lecturer_or_admin),
):
    return run_submission_processing_pipeline(
        db=db,
        submission_id=submission_id,
        created_by=current_user.id,
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
    return retry_submission_processing_job(
        db=db,
        job_id=job_id,
        created_by=current_user.id,
    )
