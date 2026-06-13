import uuid
from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Score(Base):
    __tablename__ = "scores"

    score_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    reference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("references.reference_id"),
        unique=True,
        nullable=False
    )

    authenticity_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )

    credibility_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )

    recency_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )

    relevance_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )

    format_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )

    total_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )

    label: Mapped[str | None] = mapped_column(String(30), nullable=True)