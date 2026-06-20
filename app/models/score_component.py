import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ScoreComponent(Base):
    __tablename__ = "score_components"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    citation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
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

    format_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    existence_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    credibility_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    recency_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    relevance_reason: Mapped[str | None] = mapped_column(
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
        back_populates="score_component",
    )