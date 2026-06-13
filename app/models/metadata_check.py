import uuid
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.core.database import Base

class MetadataCheck(Base):
    __tablename__ = "metadata_checks"

    metadata_check_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    reference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("references.reference_id"),
        nullable=False
    )

    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)

    matched_title: Mapped[str | None] = mapped_column(Text, nullable=True)

    matched_doi: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    confidence_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )

    checked_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )