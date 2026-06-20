from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_permissions
from app.core.permissions import COURSE_MANAGE
from app.db.session import get_db
from app.models.assignment import Assignment
from app.models.file import File as FileModel
from app.models.submission import Submission
from app.schemas.class_schema import ClassCreate, ClassRead, ClassUpdate
from app.services.audit_service import record_audit_log
from app.services.class_service import (
    create_class,
    delete_class,
    get_class_by_code,
    get_class_by_id,
    get_classes,
    get_course_by_id,
    update_class,
)


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


@router.post("", response_model=ClassRead, status_code=status.HTTP_201_CREATED)
def create_class_endpoint(
    payload: ClassCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(COURSE_MANAGE)),
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
    current_user=Depends(require_permissions(COURSE_MANAGE)),
):
    role = get_user_role(current_user)

    if role == "ADMIN":
        return get_classes(db=db)

    return get_classes(
        db=db,
        lecturer_id=current_user.id,
    )


def _submission_status(score: float | None, status_value: str | None) -> str:
    if score is None:
        return "warning" if str(status_value or "").upper() not in {"FAILED", "REJECTED"} else "fail"
    if score >= 80:
        return "pass"
    if score >= 50:
        return "warning"
    return "fail"


def _get_class_or_404(
    db: Session,
    class_identifier: str,
):
    classroom = None
    try:
        class_uuid = UUID(class_identifier)
    except (ValueError, TypeError, AttributeError):
        class_uuid = None

    if class_uuid is not None:
        classroom = get_class_by_id(db=db, class_id=class_uuid)

    if classroom is None:
        classroom = get_class_by_code(db=db, class_code=class_identifier)

    if classroom is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "CLASS_NOT_FOUND",
                "message": "Class not found.",
                "details": {"class_identifier": class_identifier},
            },
        )

    return classroom


def _ensure_class_owner_or_admin(classroom, current_user) -> None:
    if get_user_role(current_user) == "ADMIN":
        return

    if str(classroom.lecturer_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "CLASS_OWNERSHIP_FORBIDDEN",
                "message": "You do not have permission to access this class.",
                "details": {"class_id": str(classroom.id)},
            },
        )


@router.put("/{class_identifier}", response_model=ClassRead)
def update_class_endpoint(
    class_identifier: str,
    payload: ClassUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(COURSE_MANAGE)),
):
    classroom = _get_class_or_404(
        db=db,
        class_identifier=class_identifier,
    )
    _ensure_class_owner_or_admin(
        classroom=classroom,
        current_user=current_user,
    )

    if payload.class_code is not None:
        next_code = payload.class_code.strip().upper()
        if not next_code:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error_code": "CLASS_CODE_REQUIRED",
                    "message": "Mã lớp học phần không được để trống.",
                    "details": None,
                },
            )
        existing_class = get_class_by_code(db=db, class_code=next_code)
        if existing_class is not None and str(existing_class.id) != str(classroom.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error_code": "CLASS_CODE_EXISTS",
                    "message": "Mã lớp học phần đã tồn tại.",
                    "details": {"class_code": next_code},
                },
            )

    if payload.name is not None and not payload.name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "CLASS_NAME_REQUIRED",
                "message": "Tên lớp học phần không được để trống.",
                "details": None,
            },
        )

    return update_class(
        db=db,
        classroom=classroom,
        payload=payload,
    )


@router.delete("/{class_identifier}", status_code=status.HTTP_200_OK)
def delete_class_endpoint(
    class_identifier: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(COURSE_MANAGE)),
):
    classroom = _get_class_or_404(
        db=db,
        class_identifier=class_identifier,
    )
    _ensure_class_owner_or_admin(
        classroom=classroom,
        current_user=current_user,
    )

    summary = delete_class(db=db, classroom=classroom)
    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="DELETE_CLASS",
        resource_type="class",
        resource_id=str(classroom.id),
        message="Class deleted.",
        details=summary,
    )
    db.commit()

    return {
        "message": "Class deleted.",
        "class_id": str(classroom.id),
        **summary,
    }


@router.get("/{class_identifier}/submissions")
def list_class_submissions_endpoint(
    class_identifier: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(COURSE_MANAGE)),
):
    classroom = _get_class_or_404(db=db, class_identifier=class_identifier)
    _ensure_class_owner_or_admin(classroom=classroom, current_user=current_user)

    rows = db.execute(
        select(Submission, FileModel)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .outerjoin(FileModel, Submission.file_id == FileModel.id)
        .where(Assignment.class_id == classroom.id)
        .where(Assignment.deleted_at.is_(None))
        .where(Submission.deleted_at.is_(None))
        .where(or_(FileModel.id.is_(None), FileModel.is_deleted.is_(False)))
        .order_by(Submission.created_at.desc())
    ).all()

    return [
        {
            "id": str(submission.id),
            "studentName": submission.owner_label or "Student",
            "fileName": file_record.original_name if file_record is not None else "N/A",
            "date": submission.created_at.strftime("%d/%m/%Y"),
            "trustScore": int(round(submission.overall_score or 0)),
            "status": _submission_status(submission.overall_score, submission.status),
            "classId": classroom.class_code,
        }
        for submission, file_record in rows
    ]
