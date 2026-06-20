from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class JobError(BaseModel):
    error_code: str
    message: str
    details: dict | None = None
    retryable: bool = True


class JobRead(BaseModel):
    id: UUID
    submission_id: UUID
    status: str
    progress: int
    step: str
    current_step: str | None = None
    report_id: UUID | None = None
    retry_of_job_id: UUID | None = None
    error_code: str | None = None
    error_message: str | None = None
    error_details: dict | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    job_id: UUID
    submission_id: UUID
    status: str
    progress: int
    current_step: str
    started_at: datetime | None = None
    updated_at: datetime
    completed_at: datetime | None = None
    report_id: UUID | None = None
    error: JobError | None = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def from_job(cls, data):
        if not hasattr(data, "id"):
            return data
        error = None
        if data.error_code:
            error = {
                "error_code": data.error_code,
                "message": data.error_message or "Job failed.",
                "details": data.error_details,
                "retryable": not str(data.error_code).startswith(("FILE_", "PDF_", "NO_REFERENCE")),
            }
        return {
            "job_id": data.id,
            "submission_id": data.submission_id,
            "status": str(data.status).lower(),
            "progress": data.progress,
            "current_step": data.current_step or data.step,
            "started_at": data.started_at,
            "updated_at": data.updated_at or data.created_at,
            "completed_at": data.finished_at,
            "report_id": data.report_id,
            "error": error,
        }


class AnalyzeJobResponse(BaseModel):
    job_id: UUID
    submission_id: UUID
    status: str
    progress: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def from_job(cls, data):
        if not hasattr(data, "id"):
            return data
        return {
            "job_id": data.id,
            "submission_id": data.submission_id,
            "status": str(data.status).lower(),
            "progress": data.progress,
            "created_at": data.created_at,
            "retry_of_job_id": data.retry_of_job_id,
        }


class JobProcessResponse(AnalyzeJobResponse):
    retry_of_job_id: UUID | None = None


class LatestJobResponse(BaseModel):
    message: str
    submission_id: UUID
    job: JobStatusResponse | None = None
