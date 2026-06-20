from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, decode_access_token
from app.db.session import get_db
from app.schemas.auth_schema import LoginRequest, LoginResponse, RefreshRequest, RefreshResponse
from app.services.audit_service import record_audit_log
from app.services.auth_service import authenticate_user, get_user_by_id


router = APIRouter()


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
                "message": "Email hoặc mật khẩu không đúng.",
                "details": None,
            },
        )

    access_token = create_access_token(
        subject=str(user.id),
        role=user.role,
    )
    refresh_token = create_refresh_token(subject=str(user.id), role=user.role)
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
    token_payload = decode_access_token(payload.refresh_token)
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
