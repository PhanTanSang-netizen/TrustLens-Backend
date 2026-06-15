from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    user = db.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()

    if user is None:
        return None

    if not user.is_active:
        return None

    if user.password_hash is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def get_user_by_id(
    db: Session,
    user_id: str,
) -> User | None:
    try:
        parsed_user_id = UUID(user_id)
    except ValueError:
        return None

    return db.execute(
        select(User).where(User.id == parsed_user_id)
    ).scalar_one_or_none()