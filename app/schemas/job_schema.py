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