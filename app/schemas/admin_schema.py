from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr


AdminRole = Literal["ADMIN", "LECTURER", "STUDENT"]
AdminUserStatus = Literal["active", "inactive"]


class AdminUserRead(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    role: AdminRole
    status: AdminUserStatus
    department: str = "Khoa CNTT"
    createdAt: str


class AdminUserCreate(BaseModel):
    full_name: str
    email: EmailStr
    role: AdminRole = "LECTURER"
    status: AdminUserStatus = "active"
    department: str = "Khoa CNTT"
    password: str | None = None


class AdminUserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    role: AdminRole | None = None
    status: AdminUserStatus | None = None
    department: str | None = None


def serialize_admin_user(user) -> dict:
    created_at = getattr(user, "created_at", None)
    if isinstance(created_at, datetime):
        created_at_text = created_at.date().isoformat()
    else:
        created_at_text = ""

    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": str(user.role).strip().upper(),
        "status": "active" if user.is_active else "inactive",
        "department": "Khoa CNTT",
        "createdAt": created_at_text,
    }
