import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TrustScore(Base):
    __tablename__ = "trust_scores"

    __table_args__ = (
        UniqueConstraint(
            "citation_id",
            name="uq_trust_scores_citation_id",
        ),
        UniqueConstraint(
            "submission_id",
            name="uq_trust_scores_submission_id",
        ),
        CheckConstraint(
            "(citation_id IS NOT NULL AND submission_id IS NULL) OR "
            "(citation_id IS NULL AND submission_id IS NOT NULL)",
            name="ck_trust_scores_single_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    citation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    label: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    config_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    citation = relationship(
        "Citation",
        back_populates="trust_score",
    )

    submission = relationship(
        "Submission",
        back_populates="trust_score",
    )

class CitationScore(Base):
    __tablename__ = "citation_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    citation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    format_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    existence_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    credibility_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    recency_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    relevance_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    reference_trust_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    confidence_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    scoring_config_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    details_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )