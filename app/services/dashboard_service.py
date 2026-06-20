from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.class_model import ClassModel
from app.models.file import File as FileModel
from app.models.report import Report
from app.models.submission import Submission


def _status_from_score(score: float | None, fallback_status: str | None = None) -> str:
    if score is None:
        return "warning" if str(fallback_status or "").upper() not in {"FAILED", "REJECTED"} else "fail"
    if score >= 80:
        return "pass"
    if score >= 50:
        return "warning"
    return "fail"


def _relative_time(value: datetime | None) -> str:
    if value is None:
        return "N/A"
    now = datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    delta = now - value
    minutes = int(delta.total_seconds() // 60)
    if minutes < 1:
        return "Just now"
    if minutes < 60:
        return f"{minutes} minutes ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hours ago"
    days = hours // 24
    if days == 1:
        return "Yesterday"
    return f"{days} days ago"


def get_dashboard_summary(db: Session, lecturer_id: UUID | None = None) -> dict:
    query = select(
        func.count(Submission.id).label("total"),
        func.coalesce(
            func.sum(case((Submission.overall_score >= 80, 1), else_=0)),
            0,
        ).label("passed"),
        func.coalesce(
            func.sum(
                case(
                    (
                        (Submission.overall_score >= 50)
                        & (Submission.overall_score < 80),
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("warnings"),
        func.coalesce(
            func.sum(
                case(
                    (
                        (Submission.overall_score < 50)
                        | (Submission.status.in_(["FAILED", "FAILED_INTERNAL", "FAILED_VALIDATION"])),
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("critical"),
    ).select_from(Submission)

    if lecturer_id is not None:
        query = query.join(Assignment, Submission.assignment_id == Assignment.id).join(
            ClassModel,
            Assignment.class_id == ClassModel.id,
        ).where(ClassModel.lecturer_id == lecturer_id)

    row = db.execute(query).one()
    return {
        "totalSubmissions": int(row.total or 0),
        "total_submissions": int(row.total or 0),
        "passed": int(row.passed or 0),
        "verified": int(row.passed or 0),
        "warnings": int(row.warnings or 0),
        "partial": int(row.warnings or 0),
        "critical": int(row.critical or 0),
        "unknown": int(row.critical or 0),
    }


def get_recent_activities(db: Session, lecturer_id: UUID | None = None, limit: int = 10) -> list[dict]:
    query = (
        select(Submission, FileModel, ClassModel, Report)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .join(ClassModel, Assignment.class_id == ClassModel.id)
        .outerjoin(FileModel, Submission.file_id == FileModel.id)
        .outerjoin(Report, Report.submission_id == Submission.id)
        .order_by(Submission.created_at.desc())
        .limit(limit)
    )

    if lecturer_id is not None:
        query = query.where(ClassModel.lecturer_id == lecturer_id)

    rows = db.execute(query).all()
    activities = []
    for submission, file_record, classroom, report in rows:
        score = submission.overall_score
        if score is None and report is not None:
            score = report.report_trust_score
        activities.append(
            {
                "id": str(submission.id),
                "submission_id": str(submission.id),
                "student": submission.owner_label or "Student",
                "class": classroom.class_code,
                "class_code": classroom.class_code,
                "time": _relative_time(submission.created_at),
                "created_at": submission.created_at,
                "score": score,
                "status": _status_from_score(score, submission.status),
                "fileName": file_record.original_name if file_record is not None else "N/A",
            }
        )
    return activities


def get_weekly_trend(db: Session, lecturer_id: UUID | None = None) -> list[dict]:
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=6)

    query = (
        select(Submission)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .join(ClassModel, Assignment.class_id == ClassModel.id)
        .where(Submission.created_at >= datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc))
    )

    if lecturer_id is not None:
        query = query.where(ClassModel.lecturer_id == lecturer_id)

    submissions = db.execute(query).scalars().all()
    grouped: dict = {
        start_date + timedelta(days=offset): {
            "total": 0,
            "passed": 0,
        }
        for offset in range(7)
    }

    for submission in submissions:
        created_at = submission.created_at
        if created_at is None:
            continue
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        bucket = created_at.date()
        if bucket not in grouped:
            continue

        grouped[bucket]["total"] += 1
        if _status_from_score(submission.overall_score, submission.status) == "pass":
            grouped[bucket]["passed"] += 1

    labels = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]

    return [
        {
            "date": day.isoformat(),
            "label": labels[day.weekday()],
            "total": values["total"],
            "passed": values["passed"],
            "rate": round((values["passed"] / values["total"]) * 100) if values["total"] else 0,
        }
        for day, values in grouped.items()
    ]
