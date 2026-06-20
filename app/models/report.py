import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("processing_jobs.id"),
        nullable=True,
        index=True,
    )
    scoring_config_version: Mapped[str] = mapped_column(String(100), default="trust-score-v1.0", nullable=False)
    report_trust_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    overall_label: Mapped[str] = mapped_column(String(50), default="needs_review", nullable=False)
    report_penalty: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    summary: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    component_summary: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    citations_payload: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    warnings: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    submission = relationship("Submission", back_populates="reports")


class ReportExport(Base):
    __tablename__ = "report_exports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    format: Mapped[str] = mapped_column(String(20), default="pdf", nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
