from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.job_schema import JobRead


class ReferenceSectionRead(BaseModel):
    id: UUID
    submission_id: UUID
    heading: str | None = None
    raw_text: str
    start_index: int | None = None
    end_index: int | None = None
    detection_method: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DetectReferenceSectionResponse(BaseModel):
    message: str
    job: JobRead
    reference_section: ReferenceSectionRead