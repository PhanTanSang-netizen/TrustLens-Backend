from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.user_schema import UserRead, UserUpdate
from app.services.audit_service import record_audit_log


router = APIRouter()


def _get_or_create_profile(
    db: Session,
    user: User,
) -> UserProfile:
    profile = db.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    ).scalar_one_or_none()

    if profile is None:
        profile = UserProfile(
            user_id=user.id,
            university="Trường Đại học Nguyễn Tất Thành",
            faculty="Khoa Công nghệ Thông tin",
            major="Kỹ thuật Phần mềm",
            notification_enabled=True,
        )
        db.add(profile)
        db.flush()

    return profile


def _serialize_user(
    user: User,
    profile: UserProfile | None = None,
) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "permissions": user.permissions,
        "university": getattr(profile, "university", None),
        "faculty": getattr(profile, "faculty", None),
        "major": getattr(profile, "major", None),
        "notification_enabled": (
            getattr(profile, "notification_enabled", True)
            if profile is not None
            else True
        ),
        "created_at": user.created_at,
    }


@router.get("/me", response_model=UserRead)
def read_current_user(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _get_or_create_profile(db=db, user=current_user)
    db.commit()
    return _serialize_user(current_user, profile)


@router.patch("/me", response_model=UserRead)
def update_current_user(
    payload: UserUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    update_data = payload.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"] is not None:
        next_email = str(update_data["email"]).strip().lower()
        existing_user = db.execute(
            select(User).where(User.email == next_email, User.id != current_user.id)
        ).scalar_one_or_none()
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error_code": "USER_EMAIL_EXISTS",
                    "message": "Email đã được sử dụng bởi tài khoản khác.",
                    "details": {"email": next_email},
                },
            )
        current_user.email = next_email

    if "full_name" in update_data and update_data["full_name"] is not None:
        next_name = str(update_data["full_name"]).strip()
        if not next_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error_code": "USER_FULL_NAME_REQUIRED",
                    "message": "Họ tên không được để trống.",
                    "details": None,
                },
            )
        current_user.full_name = next_name

    profile = _get_or_create_profile(db=db, user=current_user)

    for field in ["university", "faculty", "major", "notification_enabled"]:
        if field in update_data:
            setattr(profile, field, update_data[field])

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="UPDATE_PROFILE",
        resource_type="user",
        resource_id=str(current_user.id),
        message="User updated profile.",
        details={key: value for key, value in update_data.items() if key != "email"},
    )
    db.commit()
    db.refresh(current_user)
    db.refresh(profile)

    return _serialize_user(current_user, profile)
