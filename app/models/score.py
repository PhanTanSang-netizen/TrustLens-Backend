import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.analysis_job import AnalysisJob


class Score(Base):
    __tablename__ = "scores"

    score_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_jobs.job_id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    source_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    recency_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    relevance_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    citation_format_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)

    total_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    classification: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    analysis_job: Mapped["AnalysisJob"] = relationship(
        back_populates="score"
    )