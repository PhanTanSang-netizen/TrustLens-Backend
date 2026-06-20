from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_permissions
from app.core.permissions import COURSE_MANAGE
from app.db.session import get_db
from app.schemas.course_schema import CourseCreate, CourseRead
from app.services.course_service import (
    create_course,
    get_course_by_code,
    get_courses,
)


router = APIRouter()


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
def create_course_endpoint(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(COURSE_MANAGE)),
):
    existing_course = get_course_by_code(
        db=db,
        code=payload.code,
    )

    if existing_course is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "COURSE_CODE_EXISTS",
                "message": "Mã học phần đã tồn tại.",
                "details": {
                    "code": payload.code,
                },
            },
        )

    return create_course(
        db=db,
        payload=payload,
    )


@router.get("", response_model=list[CourseRead])
def list_courses_endpoint(
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(COURSE_MANAGE)),
):
    return get_courses(db=db)
