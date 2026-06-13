import uuid
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Reference(Base):
    __tablename__ = "references"

    reference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.document_id"),
        nullable=False
    )

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    title: Mapped[str | None] = mapped_column(Text, nullable=True)

    authors: Mapped[str | None] = mapped_column(Text, nullable=True)

    year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    doi: Mapped[str | None] = mapped_column(String(255), nullable=True)

    source_name: Mapped[str | None] = mapped_column(Text, nullable=True)