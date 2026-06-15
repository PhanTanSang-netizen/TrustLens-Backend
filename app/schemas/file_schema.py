from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FileRead(BaseModel):
    id: UUID
    original_name: str
    stored_name: str
    stored_path: str
    mime_type: str
    size_bytes: int
    checksum: str
    uploaded_by: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)