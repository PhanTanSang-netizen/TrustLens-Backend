from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ClassCreate(BaseModel):
    course_id: UUID
    class_code: str
    name: str
    term_name: str | None = None


class ClassUpdate(BaseModel):
    class_code: str | None = None
    name: str | None = None
    term_name: str | None = None


class ClassRead(BaseModel):
    id: UUID
    course_id: UUID
    lecturer_id: UUID
    class_code: str
    name: str
    term_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
