import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CitationScore(Base):
    __tablename__ = "citation_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    citation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    scoring_config_version: Mapped[str] = mapped_column(String(100), default="trust-score-v1.0", nullable=False)
    c1: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    c2: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    c3: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    c4: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    c5: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    c6: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    c7: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    c8: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reference_trust_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    explanations: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
