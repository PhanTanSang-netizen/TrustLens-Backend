"""add extraction runtime columns

Revision ID: f4d5e6f7a8b9
Revises: f3c4d5e6f7a8
Create Date: 2026-06-20 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "f3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE extracted_documents ADD COLUMN IF NOT EXISTS char_count INTEGER")
    op.execute("ALTER TABLE extracted_documents ADD COLUMN IF NOT EXISTS language VARCHAR(20)")
    op.execute("ALTER TABLE extracted_documents ADD COLUMN IF NOT EXISTS has_text_layer BOOLEAN")


def downgrade() -> None:
    pass
