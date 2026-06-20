"""align course class assignment runtime columns

Revision ID: f2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-06-20 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE courses ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()")
    op.execute("ALTER TABLE courses ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE")

    op.execute("ALTER TABLE classes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()")
    op.execute("ALTER TABLE classes ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS scoring_configs (
            id UUID PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            weights_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            thresholds_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_by UUID NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_scoring_configs_name_version'
            ) THEN
                ALTER TABLE scoring_configs
                ADD CONSTRAINT uq_scoring_configs_name_version UNIQUE (name, version);
            END IF;
        END $$;
        """
    )

    op.execute("ALTER TABLE assignments ADD COLUMN IF NOT EXISTS scoring_config_id UUID")
    op.execute("ALTER TABLE assignments ADD COLUMN IF NOT EXISTS created_by UUID")
    op.execute("ALTER TABLE assignments ADD COLUMN IF NOT EXISTS due_date TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE assignments ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()")
    op.execute("ALTER TABLE assignments ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE")

    op.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS submitted_by UUID")
    op.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS overall_label VARCHAR(100)")
    op.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS latest_job_id UUID")
    op.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()")
    op.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE")

    op.execute("ALTER TABLE files ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE")


def downgrade() -> None:
    pass
