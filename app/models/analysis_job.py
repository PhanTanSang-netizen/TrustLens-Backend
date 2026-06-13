import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.reference import Reference
    from app.models.score import Score
    from app.models.export import Export


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="queued"
    )

    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    current_step: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )

    document: Mapped["Document"] = relationship(
        back_populates="analysis_jobs"
    )

    references: Mapped[list["Reference"]] = relationship(
        back_populates="analysis_job",
        cascade="all, delete-orphan"
    )

    score: Mapped["Score"] = relationship(
        back_populates="analysis_job",
        uselist=False,
        cascade="all, delete-orphan"
    )

    exports: Mapped[list["Export"]] = relationship(
        back_populates="analysis_job",
        cascade="all, delete-orphan"
    )