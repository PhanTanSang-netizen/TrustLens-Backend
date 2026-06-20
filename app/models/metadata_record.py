import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MetadataRecord(Base):
    __tablename__ = "metadata_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    citation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    metadata_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metadata_providers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="URL_CHECK",
    )

    query_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="url",
    )

    query_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    matched_title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    matched_authors: Mapped[dict | list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    matched_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    matched_venue: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    matched_publisher: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    matched_doi: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    source_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    citation_signal: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    verification_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="unknown",
    )

    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    error_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    provider_latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    raw_response: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    normalized_response: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    submission = relationship(
        "Submission",
        back_populates="metadata_records",
    )

    citation = relationship(
        "Citation",
        back_populates="metadata_records",
    )

    metadata_provider = relationship(
        "MetadataProvider",
        back_populates="metadata_records",
    )