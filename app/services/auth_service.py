from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User


def normalize_email(email: str) -> str:
    return email.strip().lower()


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    normalized_email = normalize_email(email)

    user = db.execute(
        select(User).where(User.email == normalized_email)
    ).scalar_one_or_none()

    if user is None:
        return None

    if not getattr(user, "is_active", True):
        return None

    if not user.password_hash:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def get_user_by_id(
    db: Session,
    user_id: str | UUID,
) -> User | None:
    try:
        if isinstance(user_id, UUID):
            parsed_user_id = user_id
        else:
            parsed_user_id = UUID(str(user_id))
    except (ValueError, TypeError, AttributeError):
        return None

    return db.execute(
        select(User).where(User.id == parsed_user_id)
    ).scalar_one_or_none()


def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    normalized_email = normalize_email(email)

    return db.execute(
        select(User).where(User.email == normalized_email)
    ).scalar_one_or_none()