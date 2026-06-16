from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.job_schema import JobRead


class MetadataRecordRead(BaseModel):
    id: UUID
    submission_id: UUID
    citation_id: UUID
    provider: str
    query_type: str
    query_value: str | None = None
    source_url: str | None = None
    matched_title: str | None = None
    matched_year: int | None = None
    verification_status: str
    confidence_score: float
    raw_response: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VerifyMetadataResponse(BaseModel):
    message: str
    total: int
    verified: int
    broken: int
    forbidden: int
    unreachable: int
    not_provided: int
    job: JobRead
    records: list[MetadataRecordRead]