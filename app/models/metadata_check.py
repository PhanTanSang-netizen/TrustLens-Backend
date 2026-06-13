import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.reference import Reference


class MetadataCheck(Base):
    __tablename__ = "metadata_checks"

    metadata_check_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    reference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("references.reference_id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    crossref_found: Mapped[bool] = mapped_column(Boolean, default=False)
    doi_valid: Mapped[bool] = mapped_column(Boolean, default=False)

    matched_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_authors: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    matched_source: Mapped[str | None] = mapped_column(Text, nullable=True)

    publisher_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    citation_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    reference: Mapped["Reference"] = relationship(
        back_populates="metadata_check"
    )