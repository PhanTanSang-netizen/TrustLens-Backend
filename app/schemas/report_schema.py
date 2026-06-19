from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReportExportCreate(BaseModel):
    format: str = "pdf"
    include_raw_citation: bool = True
    include_teacher_notes: bool = False


class ReportHistoryItem(BaseModel):
    id: UUID
    revision_number: int = 1
    report_trust_score: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
