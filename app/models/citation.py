import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, UniqueConstraint, func
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

    confidence: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    duplicate_of: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citations.id", ondelete="SET NULL"),
        nullable=True,
    )

    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    line_number: Mapped[int | None] = mapped_column(
        Integer,
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

    duplicate_source = relationship(
        "Citation",
        remote_side=[id],
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