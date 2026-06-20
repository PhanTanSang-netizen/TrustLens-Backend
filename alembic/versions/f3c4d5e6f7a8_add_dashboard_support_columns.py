"""add dashboard support columns

Revision ID: f3c4d5e6f7a8
Revises: f2b3c4d5e6f7
Create Date: 2026-06-20 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "f2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE files ADD COLUMN IF NOT EXISTS extension VARCHAR(20)")
    op.execute("ALTER TABLE files ADD COLUMN IF NOT EXISTS storage_backend VARCHAR(50) NOT NULL DEFAULT 'local'")
    op.execute("ALTER TABLE files ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT false")


def downgrade() -> None:
    pass
