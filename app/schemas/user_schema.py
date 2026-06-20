from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    permissions: list[str] = Field(default_factory=list)
    university: str | None = None
    faculty: str | None = None
    major: str | None = None
    notification_enabled: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    university: str | None = None
    faculty: str | None = None
    major: str | None = None
    notification_enabled: bool | None = None
