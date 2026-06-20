from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AssignmentCreate(BaseModel):
    class_id: UUID
    title: str
    description: str | None = None
    required_style: str | None = None
    status: str = "OPEN"
    due_date: datetime | None = None


class AssignmentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    required_style: str | None = None
    status: str | None = None
    due_date: datetime | None = None


class AssignmentRead(BaseModel):
    id: UUID
    class_id: UUID
    title: str
    description: str | None = None
    required_style: str | None = None
    status: str
    due_date: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
