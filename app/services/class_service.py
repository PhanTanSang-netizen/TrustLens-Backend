from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.class_model import ClassModel
from app.models.course import Course
from app.schemas.class_schema import ClassCreate


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
        select(ClassModel).where(ClassModel.class_code == class_code)
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
) -> list[ClassModel]:
    return list(
        db.execute(
            select(ClassModel).order_by(ClassModel.created_at.desc())
        ).scalars().all()
    )