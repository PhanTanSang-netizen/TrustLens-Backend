from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.class_model import ClassModel
from app.models.course import Course
from app.models.file import File as FileModel
from app.models.submission import Submission
from app.schemas.class_schema import ClassCreate, ClassUpdate


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _deleted_class_code(class_code: str, deleted_at: datetime) -> str:
    suffix = f"__deleted__{int(deleted_at.timestamp())}"
    return f"{class_code[: 50 - len(suffix)]}{suffix}"


def get_course_by_id(
    db: Session,
    course_id: UUID,
) -> Course | None:
    return db.execute(
        select(Course).where(Course.id == course_id)
    ).scalar_one_or_none()


def get_class_by_code(
    db: Session,
    class_code: str,
) -> ClassModel | None:
    return db.execute(
        select(ClassModel).where(
            ClassModel.class_code == class_code,
            ClassModel.deleted_at.is_(None),
        )
    ).scalar_one_or_none()


def get_class_by_id(
    db: Session,
    class_id: UUID,
) -> ClassModel | None:
    return db.execute(
        select(ClassModel).where(
            ClassModel.id == class_id,
            ClassModel.deleted_at.is_(None),
        )
    ).scalar_one_or_none()


def create_class(
    db: Session,
    payload: ClassCreate,
    lecturer_id: UUID,
) -> ClassModel:
    classroom = ClassModel(
        course_id=payload.course_id,
        lecturer_id=lecturer_id,
        class_code=payload.class_code,
        name=payload.name,
        term_name=payload.term_name,
    )

    db.add(classroom)
    db.commit()
    db.refresh(classroom)

    return classroom


def get_classes(
    db: Session,
    lecturer_id: UUID | None = None,
) -> list[ClassModel]:
    query = select(ClassModel).where(ClassModel.deleted_at.is_(None))

    if lecturer_id is not None:
        query = query.where(ClassModel.lecturer_id == lecturer_id)

    query = query.order_by(ClassModel.created_at.desc())

    return list(
        db.execute(query).scalars().all()
    )


def update_class(
    db: Session,
    classroom: ClassModel,
    payload: ClassUpdate,
) -> ClassModel:
    update_data = payload.model_dump(exclude_unset=True)

    if "class_code" in update_data and update_data["class_code"] is not None:
        classroom.class_code = update_data["class_code"].strip().upper()

    if "name" in update_data and update_data["name"] is not None:
        classroom.name = update_data["name"].strip()

    if "term_name" in update_data:
        classroom.term_name = (
            update_data["term_name"].strip()
            if isinstance(update_data["term_name"], str)
            else update_data["term_name"]
        )

    db.commit()
    db.refresh(classroom)

    return classroom


def delete_class(
    db: Session,
    classroom: ClassModel,
) -> dict[str, int]:
    deleted_at = _utcnow()

    assignments = list(
        db.execute(
            select(Assignment).where(
                Assignment.class_id == classroom.id,
                Assignment.deleted_at.is_(None),
            )
        ).scalars().all()
    )

    submission_rows = db.execute(
        select(Submission, FileModel)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .outerjoin(FileModel, Submission.file_id == FileModel.id)
        .where(
            Assignment.class_id == classroom.id,
            Submission.deleted_at.is_(None),
        )
    ).all()

    for submission, file_record in submission_rows:
        submission.deleted_at = deleted_at
        submission.status = "DELETED"
        if file_record is not None:
            file_record.is_deleted = True
            file_record.deleted_at = deleted_at

    for assignment in assignments:
        assignment.deleted_at = deleted_at
        assignment.status = "DELETED"

    classroom.deleted_at = deleted_at
    classroom.class_code = _deleted_class_code(classroom.class_code, deleted_at)

    db.commit()

    return {
        "assignments_deleted": len(assignments),
        "submissions_deleted": len(submission_rows),
        "files_deleted": len([row for row in submission_rows if row[1] is not None]),
    }
