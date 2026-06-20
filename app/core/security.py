from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
    pbkdf2_sha256__default_rounds=390000,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_role(role: str | None) -> str:
    if role is None:
        return ""

    return str(role).strip().upper()


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    if not plain_password or not hashed_password:
        return False

    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


def get_password_hash(
    password: str,
) -> str:
    return pwd_context.hash(password)


def is_password_strong_enough(
    password: str,
) -> bool:
    """
    MVP password policy:
    - Ít nhất 6 ký tự để không phá demo user hiện tại.
    - Sau này production nên nâng lên 8–12 ký tự, có chữ hoa/thường/số/ký tự đặc biệt.
    """

    if not password:
        return False

    return len(password) >= 6


def create_access_token(
    subject: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    issued_at = utc_now()

    expire = issued_at + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": normalize_role(role),
        "type": "access",
        "iat": issued_at,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_token(
    token: str,
) -> dict[str, Any] | None:
    if not token or not token.strip():
        return None

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        token_type = payload.get("type") or payload.get("token_type")

        # Backward-compatible:
        # Token cũ chưa có "type" vẫn được chấp nhận.
        # Nếu token đã có type thì bắt buộc phải là access.
        if token_type is not None and token_type != "access":
            return None

        if payload.get("sub") is None:
            return None

        return payload

    except JWTError:
        return None