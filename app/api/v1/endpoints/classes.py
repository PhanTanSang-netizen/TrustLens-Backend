from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.class_schema import ClassCreate, ClassRead
from app.services.class_service import (
    create_class,
    get_class_by_code,
    get_classes,
    get_course_by_id,
)


router = APIRouter()


@router.post("", response_model=ClassRead, status_code=status.HTTP_201_CREATED)
def create_class_endpoint(
    payload: ClassCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    course = get_course_by_id(
        db=db,
        course_id=payload.course_id,
    )

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "COURSE_NOT_FOUND",
                "message": "Không tìm thấy học phần.",
                "details": {
                    "course_id": str(payload.course_id),
                },
            },
        )

    existing_class = get_class_by_code(
        db=db,
        class_code=payload.class_code,
    )

    if existing_class is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "CLASS_CODE_EXISTS",
                "message": "Mã lớp học phần đã tồn tại.",
                "details": {
                    "class_code": payload.class_code,
                },
            },
        )

    return create_class(
        db=db,
        payload=payload,
        lecturer_id=current_user.id,
    )


@router.get("", response_model=list[ClassRead])
def list_classes_endpoint(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return get_classes(
        db=db,
        lecturer_id=None if current_user.role == "admin" else current_user.id,
    )
