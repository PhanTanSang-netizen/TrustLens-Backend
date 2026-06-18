from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JobRead(BaseModel):
    id: UUID
    submission_id: UUID
    status: str
    progress: int
    step: str
    error_code: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobPipelineResult(BaseModel):
    extracted_document_id: str | None = None
    reference_section_id: str | None = None
    citation_count: int = 0
    metadata_record_count: int = 0


class JobProcessResponse(BaseModel):
    message: str
    submission_id: str
    job: JobRead
    result: JobPipelineResult


class LatestJobResponse(BaseModel):
    message: str
    submission_id: str
    job: JobRead | None = None