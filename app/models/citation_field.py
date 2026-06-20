import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CitationField(Base):
    __tablename__ = "citation_fields"

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

    style_detected: Mapped[str] = mapped_column(
        String(50),
        default="UNKNOWN",
        nullable=False,
    )

    style_confidence: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    authors: Mapped[dict | list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    doi: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    venue: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    publisher: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    normalized_title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    normalized_doi: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    normalized_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    field_confidence_json: Mapped[dict | None] = mapped_column(
        JSONB,
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

    citation = relationship(
        "Citation",
        back_populates="fields",
    )