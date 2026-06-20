from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.file_schema import FileRead
from app.schemas.job_schema import JobRead


class SubmissionRead(BaseModel):
    id: UUID
    assignment_id: UUID
    file_id: UUID
    owner_label: str | None = None
    status: str
    overall_score: float | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionUploadResponse(BaseModel):
    message: str
    id: UUID
    submission_id: UUID
    file_id: UUID
    job_id: UUID
    status: str
    submission: SubmissionRead
    file: FileRead
    job: JobRead

class AnalyzeSubmissionResponse(BaseModel):
    submission_id: UUID
    job_id: UUID | None = None
    status: str
    message: str = "Submission analysis accepted."