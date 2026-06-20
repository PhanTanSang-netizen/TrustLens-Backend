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
    if not password:
        return False

    return len(password) >= 6


def _decode_token(token: str) -> dict[str, Any] | None:
    if not token or not token.strip():
        return None

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        return None

    if payload.get("sub") is None:
        return None

    return payload


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


def decode_access_token(token: str) -> dict[str, Any] | None:
    payload = _decode_token(token)

    if payload is None:
        return None

    token_type = payload.get("type") or payload.get("token_type")

    # Backward-compatible: old tokens without a type are accepted as access tokens.
    if token_type is not None and token_type != "access":
        return None

    return payload


def create_refresh_token(
    subject: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    issued_at = utc_now()
    expire = issued_at + (
        expires_delta if expires_delta is not None else timedelta(days=7)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": normalize_role(role),
        "type": "refresh",
        "iat": issued_at,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_refresh_token(token: str) -> dict[str, Any] | None:
    payload = _decode_token(token)

    if payload is None:
        return None

    if payload.get("type") != "refresh":
        return None

    return payload
