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

        error_code = getattr(data, "error_code", None)
        error_message = getattr(data, "error_message", None)
        error_details = getattr(data, "error_details", None)

        error = None
        if error_code:
            error = {
                "error_code": error_code,
                "message": error_message or "Job failed.",
                "details": error_details,
                "retryable": not str(error_code).startswith(
                    ("FILE_", "PDF_", "NO_REFERENCE")
                ),
            }

        current_step = (
            getattr(data, "current_step", None)
            or getattr(data, "step", None)
            or "queued"
        )

        return {
            "job_id": data.id,
            "submission_id": data.submission_id,
            "status": str(getattr(data, "status", "QUEUED")).lower(),
            "progress": getattr(data, "progress", 0),
            "current_step": current_step,
            "started_at": getattr(data, "started_at", None),
            "updated_at": getattr(data, "updated_at", None)
            or getattr(data, "created_at", None),
            "completed_at": getattr(data, "finished_at", None),
            "report_id": getattr(data, "report_id", None),
            "error": error,
        }


class AnalyzeJobResponse(BaseModel):
    job_id: UUID
    submission_id: UUID
    status: str
    progress: int
    created_at: datetime


class JobProcessResponse(BaseModel):
    job_id: UUID
    submission_id: UUID
    status: str
    progress: int
    step: str | None = None
    message: str = "Processing job accepted."


class JobRetryResponse(BaseModel):
    old_job_id: UUID
    new_job_id: UUID
    submission_id: UUID
    status: str = "QUEUED"
    message: str = "Retry job created."

class LatestJobResponse(BaseModel):
    found: bool = True

    job_id: UUID | None = None
    submission_id: UUID | None = None

    status: str | None = None
    progress: int | None = None
    current_step: str | None = None

    started_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None

    report_id: UUID | None = None
    error: JobError | None = None

    message: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def from_job(cls, data):
        if data is None:
            return {
                "found": False,
                "message": "No processing job found for this submission.",
            }

        if isinstance(data, dict):
            return data

        if not hasattr(data, "id"):
            return data

        error_code = getattr(data, "error_code", None)
        error_message = getattr(data, "error_message", None)
        error_details = getattr(data, "error_details", None)

        error = None
        if error_code:
            error = {
                "error_code": error_code,
                "message": error_message or "Job failed.",
                "details": error_details,
                "retryable": not str(error_code).startswith(
                    ("FILE_", "PDF_", "NO_REFERENCE")
                ),
            }

        current_step = (
            getattr(data, "current_step", None)
            or getattr(data, "step", None)
            or "queued"
        )

        return {
            "found": True,
            "job_id": data.id,
            "submission_id": data.submission_id,
            "status": str(getattr(data, "status", "QUEUED")).lower(),
            "progress": getattr(data, "progress", 0),
            "current_step": current_step,
            "started_at": getattr(data, "started_at", None),
            "updated_at": getattr(data, "updated_at", None)
            or getattr(data, "created_at", None),
            "completed_at": getattr(data, "finished_at", None),
            "report_id": getattr(data, "report_id", None),
            "error": error,
        }