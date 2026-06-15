from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.job_schema import JobRead


class ExtractedDocumentRead(BaseModel):
    id: UUID
    submission_id: UUID
    full_text: str
    page_count: int | None = None
    word_count: int | None = None
    extraction_method: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalyzeSubmissionResponse(BaseModel):
    message: str
    job: JobRead
    extracted_document: ExtractedDocumentRead