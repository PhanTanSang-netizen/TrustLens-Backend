from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.class_model import ClassModel
from app.schemas.assignment_schema import AssignmentCreate, AssignmentUpdate


def get_class_by_id(
    db: Session,
    class_id: UUID,
) -> ClassModel | None:
    return db.execute(
        select(ClassModel).where(ClassModel.id == class_id)
    ).scalar_one_or_none()


def get_assignment_by_class_and_title(
    db: Session,
    class_id: UUID,
    title: str,
) -> Assignment | None:
    return db.execute(
        select(Assignment).where(
            Assignment.class_id == class_id,
            Assignment.title == title,
        )
    ).scalar_one_or_none()


def create_assignment(
    db: Session,
    payload: AssignmentCreate,
) -> Assignment:
    assignment = Assignment(
        class_id=payload.class_id,
        title=payload.title,
        description=payload.description,
        required_style=payload.required_style,
        status=payload.status,
        due_date=payload.due_date,
    )

    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return assignment


def get_assignment_by_id(
    db: Session,
    assignment_id: UUID,
) -> Assignment | None:
    return db.execute(
        select(Assignment).where(Assignment.id == assignment_id)
    ).scalar_one_or_none()


def update_assignment(
    db: Session,
    assignment: Assignment,
    payload: AssignmentUpdate,
) -> Assignment:
    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(assignment, field, value)

    db.commit()
    db.refresh(assignment)

    return assignment


def get_assignments(
    db: Session,
    class_id: UUID | None = None,
    lecturer_id: UUID | None = None,
) -> list[Assignment]:
    query = select(Assignment).join(
        ClassModel,
        Assignment.class_id == ClassModel.id,
    )

    if class_id is not None:
        query = query.where(Assignment.class_id == class_id)

    if lecturer_id is not None:
        query = query.where(ClassModel.lecturer_id == lecturer_id)

    query = query.order_by(Assignment.created_at.desc())

    return list(
        db.execute(query).scalars().all()
    )
