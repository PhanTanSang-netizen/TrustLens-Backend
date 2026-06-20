from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.permissions import has_any_permission
from app.core.security import decode_access_token
from app.db.session import get_db
from app.services.auth_service import get_user_by_id


bearer_scheme = HTTPBearer(auto_error=False)


def _auth_error(
    error_code: str,
    message: str,
    status_code: int = status.HTTP_401_UNAUTHORIZED,
    details: Any = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "error_code": error_code,
            "message": message,
            "details": details,
        },
    )


def _permission_error(
    error_code: str = "AUTH_FORBIDDEN",
    message: str = "Bạn không có quyền thực hiện thao tác này.",
    details: Any = None,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error_code": error_code,
            "message": message,
            "details": details,
        },
    )


def _normalize_role(role: Any) -> str:
    if role is None:
        return ""

    return str(role).strip().upper()


def _is_user_active(user: Any) -> bool:
    """
    Hỗ trợ nhiều kiểu field:
    - is_active: bool
    - active: bool
    - status: ACTIVE / INACTIVE / DISABLED / SUSPENDED / LOCKED
    """

    if hasattr(user, "is_active"):
        return bool(getattr(user, "is_active"))

    if hasattr(user, "active"):
        return bool(getattr(user, "active"))

    if hasattr(user, "status"):
        status_value = str(getattr(user, "status") or "").strip().upper()

        if status_value in ["INACTIVE", "DISABLED", "SUSPENDED", "LOCKED"]:
            return False

    return True


def _get_user_role(user: Any) -> str:
    return _normalize_role(getattr(user, "role", None))


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise _auth_error(
            error_code="AUTH_REQUIRED",
            message="Thiếu Authorization Bearer token.",
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise _auth_error(
            error_code="AUTH_INVALID_TOKEN",
            message="Token không hợp lệ hoặc đã hết hạn.",
        )

    user_id = payload.get("sub")

    if user_id is None:
        raise _auth_error(
            error_code="AUTH_INVALID_TOKEN_PAYLOAD",
            message="Token thiếu thông tin người dùng.",
        )

    try:
        user_uuid = UUID(str(user_id))
    except ValueError as exc:
        raise _auth_error(
            error_code="AUTH_INVALID_USER_ID",
            message="Token chứa user_id không hợp lệ.",
            details={
                "user_id": str(user_id),
            },
        ) from exc

    # auth_service.get_user_by_id hiện đang parse UUID từ string,
    # nên truyền str(user_uuid) để tránh lỗi UUID bị parse 2 lần.
    user = get_user_by_id(
        db=db,
        user_id=str(user_uuid),
    )

    if user is None:
        raise _auth_error(
            error_code="AUTH_USER_NOT_FOUND",
            message="Không tìm thấy người dùng từ token.",
        )

    if not _is_user_active(user):
        raise _auth_error(
            error_code="AUTH_USER_INACTIVE",
            message="Tài khoản đã bị vô hiệu hóa hoặc chưa được kích hoạt.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    return user


def require_roles(
    *allowed_roles: str,
) -> Callable:
    normalized_allowed_roles = {
        _normalize_role(role)
        for role in allowed_roles
    }

    def dependency(
        current_user=Depends(get_current_user),
    ):
        user_role = _get_user_role(current_user)

        if user_role not in normalized_allowed_roles:
            raise _permission_error(
                error_code="AUTH_ROLE_FORBIDDEN",
                message="Vai trò người dùng không được phép thực hiện thao tác này.",
                details={
                    "required_roles": sorted(normalized_allowed_roles),
                    "current_role": user_role,
                },
            )

        return current_user

    return dependency


def require_permissions(
    *permissions: str,
) -> Callable:
    required_permissions = tuple(permissions)

    def dependency(
        current_user=Depends(get_current_user),
    ):
        user_role = _get_user_role(current_user)

        if not has_any_permission(user_role, required_permissions):
            raise _permission_error(
                error_code="AUTH_PERMISSION_FORBIDDEN",
                message="Tài khoản không có quyền thực hiện chức năng này.",
                details={
                    "required_permissions": sorted(required_permissions),
                    "current_role": user_role,
                },
            )

        return current_user

    return dependency


def get_current_admin_user(
    current_user=Depends(require_roles("ADMIN")),
):
    return current_user


def get_current_lecturer_or_admin(
    current_user=Depends(require_roles("LECTURER", "ADMIN")),
):
    return current_user


def get_current_student_lecturer_or_admin(
    current_user=Depends(require_roles("STUDENT", "LECTURER", "ADMIN")),
):
    return current_user


def ensure_admin(
    user: Any,
) -> None:
    if _get_user_role(user) != "ADMIN":
        raise _permission_error(
            error_code="AUTH_ADMIN_REQUIRED",
            message="Chỉ quản trị viên mới được thực hiện thao tác này.",
        )


def ensure_role_in(
    user: Any,
    allowed_roles: list[str] | tuple[str, ...] | set[str],
) -> None:
    normalized_allowed_roles = {
        _normalize_role(role)
        for role in allowed_roles
    }

    user_role = _get_user_role(user)

    if user_role not in normalized_allowed_roles:
        raise _permission_error(
            error_code="AUTH_ROLE_FORBIDDEN",
            message="Vai trò người dùng không được phép thực hiện thao tác này.",
            details={
                "required_roles": sorted(normalized_allowed_roles),
                "current_role": user_role,
            },
        )


def ensure_owner_or_admin(
    current_user: Any,
    owner_id: UUID | str | None,
) -> None:
    if owner_id is None:
        raise _permission_error(
            error_code="AUTH_OWNER_UNKNOWN",
            message="Không xác định được chủ sở hữu tài nguyên.",
        )

    if _get_user_role(current_user) == "ADMIN":
        return

    current_user_id = str(getattr(current_user, "id", ""))
    owner_id_text = str(owner_id)

    if current_user_id != owner_id_text:
        raise _permission_error(
            error_code="AUTH_OWNERSHIP_FORBIDDEN",
            message="Bạn không có quyền truy cập tài nguyên không thuộc phạm vi của mình.",
            details={
                "current_user_id": current_user_id,
                "owner_id": owner_id_text,
            },
        )
    
def require_admin(
    current_user=Depends(require_roles("ADMIN")),
):
    """
    Dependency kiểm tra quyền admin.

    Dùng cho endpoint admin:
    current_user = Depends(require_admin)
    """

    role = str(getattr(current_user, "role", "")).strip().lower()

    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "AUTH_ADMIN_REQUIRED",
                "message": "Bạn cần quyền admin để truy cập chức năng này.",
                "details": {
                    "current_role": role,
                },
            },
        )

    return current_user
