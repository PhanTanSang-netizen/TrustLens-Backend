from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.user import User


DEMO_EMAIL = "lecturer@trustlens.vn"
DEMO_PASSWORD = "123456"


def seed_auth_user():
    db = SessionLocal()

    try:
        user = db.execute(
            select(User).where(User.email == DEMO_EMAIL)
        ).scalar_one_or_none()

        if user is None:
            user = User(
                email=DEMO_EMAIL,
                full_name="Demo Lecturer",
                role="lecturer",
                password_hash=get_password_hash(DEMO_PASSWORD),
                is_active=True,
            )
            db.add(user)
        else:
            user.full_name = "Demo Lecturer"
            user.role = "lecturer"
            user.password_hash = get_password_hash(DEMO_PASSWORD)
            user.is_active = True

        db.commit()

        print("Demo auth user is ready.")
        print(f"email    = {DEMO_EMAIL}")
        print(f"password = {DEMO_PASSWORD}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_auth_user()