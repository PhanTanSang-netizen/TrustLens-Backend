from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_permissions
from app.core.permissions import ASSIGNMENT_MANAGE
from app.db.session import get_db
from app.schemas.assignment_schema import AssignmentCreate, AssignmentRead, AssignmentUpdate
from app.services.assignment_service import (
    create_assignment,
    get_assignment_by_id,
    get_assignment_by_class_and_title,
    get_assignments,
    get_class_by_id,
    update_assignment,
)
from app.services.access_control_service import ensure_class_access


router = APIRouter()


def get_user_role(current_user) -> str:
    return str(getattr(current_user, "role", "")).strip().upper()


def require_lecturer_or_admin(current_user) -> None:
    role = get_user_role(current_user)

    if role not in ["LECTURER", "ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "AUTH_ROLE_FORBIDDEN",
                "message": "Chỉ giảng viên hoặc quản trị viên được thực hiện thao tác này.",
                "details": {
                    "current_role": role,
                    "required_roles": ["LECTURER", "ADMIN"],
                },
            },
        )


def ensure_class_owner_or_admin(
    classroom,
    current_user,
) -> None:
    role = get_user_role(current_user)

    if role == "ADMIN":
        return

    if str(classroom.lecturer_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "CLASS_OWNERSHIP_FORBIDDEN",
                "message": "Bạn không có quyền thao tác trên lớp học phần này.",
                "details": {
                    "class_id": str(classroom.id),
                    "class_lecturer_id": str(classroom.lecturer_id),
                    "current_user_id": str(current_user.id),
                },
            },
        )


@router.post("", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
def create_assignment_endpoint(
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(ASSIGNMENT_MANAGE)),
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

    ensure_class_owner_or_admin(
        classroom=classroom,
        current_user=current_user,
    )

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
    current_user=Depends(require_permissions(ASSIGNMENT_MANAGE)),
):
    role = get_user_role(current_user)

    if class_id is not None:
        classroom = get_class_by_id(
            db=db,
            class_id=class_id,
        )

        if classroom is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "CLASS_NOT_FOUND",
                    "message": "Không tìm thấy lớp học phần.",
                    "details": {
                        "class_id": str(class_id),
                    },
                },
            )

        ensure_class_owner_or_admin(
            classroom=classroom,
            current_user=current_user,
        )

    if role == "ADMIN":
        return get_assignments(
            db=db,
            class_id=class_id,
        )

    return get_assignments(
        db=db,
        class_id=class_id,
        lecturer_id=current_user.id,
    )


@router.patch("/{assignment_id}", response_model=AssignmentRead)
def update_assignment_endpoint(
    assignment_id: UUID,
    payload: AssignmentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(ASSIGNMENT_MANAGE)),
):
    assignment = get_assignment_by_id(
        db=db,
        assignment_id=assignment_id,
    )

    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "ASSIGNMENT_NOT_FOUND",
                "message": "Khong tim thay bai nop.",
                "details": {
                    "assignment_id": str(assignment_id),
                },
            },
        )

    classroom = get_class_by_id(
        db=db,
        class_id=assignment.class_id,
    )

    if classroom is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "CLASS_NOT_FOUND",
                "message": "Khong tim thay lop hoc phan.",
                "details": {
                    "class_id": str(assignment.class_id),
                },
            },
        )

    ensure_class_owner_or_admin(
        classroom=classroom,
        current_user=current_user,
    )

    return update_assignment(
        db=db,
        assignment=assignment,
        payload=payload,
    )
