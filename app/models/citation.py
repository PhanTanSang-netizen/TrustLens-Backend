import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Citation(Base):
    __tablename__ = "citations"

    __table_args__ = (
        UniqueConstraint(
            "submission_id",
            "sequence_no",
            name="uq_citations_submission_sequence",
        ),
    )

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

    reference_section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reference_sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sequence_no: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    raw_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    detected_style: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    authors: Mapped[str | None] = mapped_column(
        Text,
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    submission = relationship(
        "Submission",
        back_populates="citations",
    )

    reference_section = relationship(
        "ReferenceSection",
        back_populates="citations",
    )

    fields = relationship(
        "CitationField",
        back_populates="citation",
        uselist=False,
    )

    metadata_records = relationship(
        "MetadataRecord",
        back_populates="citation",
    )

    score_component = relationship(
        "ScoreComponent",
        back_populates="citation",
        uselist=False,
    )

    trust_score = relationship(
        "TrustScore",
        back_populates="citation",
        uselist=False,
    )

    warnings = relationship(
        "Warning",
        back_populates="citation",
    )
