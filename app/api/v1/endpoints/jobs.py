from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.job_schema import JobStatusResponse
from app.services.access_control_service import get_accessible_job_or_404
from app.services.analysis_pipeline_service import run_analysis_pipeline
from app.services.audit_service import record_audit_log
from app.services.job_service import ACTIVE_JOB_STATUSES, create_queued_job, get_active_job_for_submission


router = APIRouter()


class RetryJobRequest(BaseModel):
    mode: str = "full"
    reason: str | None = None


@router.get("/{job_id}", response_model=JobStatusResponse)
def read_job_status(job_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return get_accessible_job_or_404(db=db, job_id=job_id, user=current_user)


@router.post("/{job_id}/retry")
def retry_job(job_id: UUID, payload: RetryJobRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    old_job = get_accessible_job_or_404(db=db, job_id=job_id, user=current_user)
    active_job = get_active_job_for_submission(db=db, submission_id=old_job.submission_id)
    if active_job is not None and active_job.id != old_job.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": "ANALYSIS_ALREADY_RUNNING", "message": "Another job is already running.", "details": {"job_id": str(active_job.id)}})
    if old_job.status in ACTIVE_JOB_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": "ANALYSIS_ALREADY_RUNNING", "message": "This job is still active.", "details": {"job_id": str(old_job.id)}})
    new_job = create_queued_job(db=db, submission_id=old_job.submission_id, created_by=current_user.id, retry_of_job_id=old_job.id)
    record_audit_log(db=db, user_id=current_user.id, action="RETRY_JOB", resource_type="processing_job", resource_id=str(new_job.id), message="Analysis retry requested.", details={"retry_of_job_id": str(old_job.id), "mode": payload.mode, "reason": payload.reason})
    db.commit()
    background_tasks.add_task(run_analysis_pipeline, str(new_job.id))
    return {"job_id": new_job.id, "status": str(new_job.status).lower()}
