import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReferenceSection(Base):
    __tablename__ = "reference_sections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    heading: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    raw_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    start_index: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    end_index: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    detection_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="heading_keyword",
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )