from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.job_schema import JobRead


class CitationRead(BaseModel):
    id: UUID
    submission_id: UUID
    reference_section_id: UUID
    sequence_no: int
    raw_text: str
    detected_style: str
    authors: str | None = None
    title: str | None = None
    year: int | None = None
    doi: str | None = None
    url: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ParseCitationsResponse(BaseModel):
    message: str
    total: int
    job: JobRead
    citations: list[CitationRead]