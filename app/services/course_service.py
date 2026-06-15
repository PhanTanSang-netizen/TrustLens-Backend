from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course import Course
from app.schemas.course_schema import CourseCreate


def create_course(
    db: Session,
    payload: CourseCreate,
) -> Course:
    course = Course(
        code=payload.code,
        name=payload.name,
        description=payload.description,
    )

    db.add(course)
    db.commit()
    db.refresh(course)

    return course


def get_courses(
    db: Session,
) -> list[Course]:
    return list(
        db.execute(
            select(Course).order_by(Course.created_at.desc())
        ).scalars().all()
    )


def get_course_by_code(
    db: Session,
    code: str,
) -> Course | None:
    return db.execute(
        select(Course).where(Course.code == code)
    ).scalar_one_or_none()