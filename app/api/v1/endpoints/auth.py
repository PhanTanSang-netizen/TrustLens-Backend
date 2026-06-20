from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    is_password_strong_enough,
    utc_now,
)
from app.db.session import get_db
from app.schemas.auth_schema import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.services.audit_service import record_audit_log
from app.services.auth_service import authenticate_user, create_user, get_user_by_email, get_user_by_id


router = APIRouter()


def _register(
    payload: RegisterRequest,
    db: Session,
) -> dict:
    if not payload.full_name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "AUTH_FULL_NAME_REQUIRED",
                "message": "Full name is required.",
                "details": None,
            },
        )

    if not is_password_strong_enough(payload.password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "AUTH_WEAK_PASSWORD",
                "message": "Password must be at least 6 characters.",
                "details": None,
            },
        )

    if get_user_by_email(db=db, email=payload.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "AUTH_EMAIL_ALREADY_EXISTS",
                "message": "Email is already registered.",
                "details": None,
            },
        )

    try:
        user = create_user(
            db=db,
            email=payload.email,
            full_name=payload.full_name,
            password=payload.password,
        )
        record_audit_log(
            db=db,
            user_id=user.id,
            action="SIGN_UP",
            resource_type="auth",
            message="User signed up.",
        )
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "AUTH_EMAIL_ALREADY_EXISTS",
                "message": "Email is already registered.",
                "details": None,
            },
        )
    except Exception:
        db.rollback()
        raise

    return {
        "message": "Sign-up successful.",
        "user": user,
    }


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
):
    return _register(payload=payload, db=db)


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    user = authenticate_user(
        db=db,
        email=payload.email,
        password=payload.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "AUTH_INVALID_CREDENTIALS",
                "message": "Email ho?c m?t kh?u kh?ng ??ng.",
                "details": None,
            },
        )

    access_token = create_access_token(
        subject=str(user.id),
        role=user.role,
    )
    refresh_token = create_refresh_token(subject=str(user.id), role=user.role)
    user.last_login_at = utc_now()
    record_audit_log(
        db=db,
        user_id=user.id,
        action="LOGIN",
        resource_type="auth",
        message="User logged in.",
    )
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/refresh", response_model=RefreshResponse)
def refresh_token(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
):
    token_payload = decode_refresh_token(payload.refresh_token)
    if token_payload is None or token_payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "AUTH_INVALID_REFRESH_TOKEN",
                "message": "Refresh token is invalid or expired.",
                "details": None,
            },
        )
    user = get_user_by_id(db=db, user_id=token_payload.get("sub", ""))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "AUTH_USER_NOT_FOUND",
                "message": "No active user found for refresh token.",
                "details": None,
            },
        )
    return {"access_token": create_access_token(subject=str(user.id), role=user.role), "token_type": "bearer"}

