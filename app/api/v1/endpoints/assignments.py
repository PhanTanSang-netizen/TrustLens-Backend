from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.assignment_schema import AssignmentCreate, AssignmentRead
from app.services.assignment_service import (
    create_assignment,
    get_assignment_by_class_and_title,
    get_assignments,
    get_class_by_id,
)
from app.services.access_control_service import ensure_class_access


router = APIRouter()


@router.post("", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
def create_assignment_endpoint(
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    classroom = get_class_by_id(
        db=db,
        class_id=payload.class_id,
    )

    if classroom is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "CLASS_NOT_FOUND",
                "message": "Không tìm thấy lớp học phần.",
                "details": {
                    "class_id": str(payload.class_id),
                },
            },
        )

    ensure_class_access(current_user, classroom)

    existing_assignment = get_assignment_by_class_and_title(
        db=db,
        class_id=payload.class_id,
        title=payload.title,
    )

    if existing_assignment is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "ASSIGNMENT_TITLE_EXISTS",
                "message": "Tên bài nộp đã tồn tại trong lớp học phần này.",
                "details": {
                    "class_id": str(payload.class_id),
                    "title": payload.title,
                },
            },
        )

    return create_assignment(
        db=db,
        payload=payload,
    )


@router.get("", response_model=list[AssignmentRead])
def list_assignments_endpoint(
    class_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if class_id is not None:
        classroom = get_class_by_id(db=db, class_id=class_id)
        if classroom is not None:
            ensure_class_access(current_user, classroom)

    return get_assignments(
        db=db,
        class_id=class_id,
        lecturer_id=None if current_user.role == "admin" else current_user.id,
    )
