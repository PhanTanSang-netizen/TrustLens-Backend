from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CourseCreate(BaseModel):
    code: str
    name: str
    description: str | None = None


class CourseRead(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)