from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: UUID
    action: str
    user: str
    time: datetime
    type: str
    message: str | None = None
    details: dict | None = None
