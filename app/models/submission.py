import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assignments.id"),
        nullable=False,
    )

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id"),
        nullable=False,
    )

    submitted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    owner_label: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="UPLOADED",
        nullable=False,
    )

    overall_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    overall_label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    latest_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    assignment = relationship(
        "Assignment",
        back_populates="submissions",
    )

    file = relationship(
        "File",
        back_populates="submission",
    )

    submitter = relationship(
        "User",
        back_populates="submitted_submissions",
    )

    processing_jobs = relationship(
        "ProcessingJob",
        back_populates="submission",
    )

    extracted_document = relationship(
        "ExtractedDocument",
        back_populates="submission",
        uselist=False,
    )

    reference_section = relationship(
        "ReferenceSection",
        back_populates="submission",
        uselist=False,
    )

    citations = relationship(
        "Citation",
        back_populates="submission",
    )

    metadata_records = relationship(
        "MetadataRecord",
        back_populates="submission",
    )

    reports = relationship(
        "Report",
        back_populates="submission",
    )

    warnings = relationship(
        "Warning",
        back_populates="submission",
    )

    trust_score = relationship(
        "TrustScore",
        back_populates="submission",
        uselist=False,
    )