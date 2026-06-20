"""align runtime models with p0 docs

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d2
Create Date: 2026-06-20 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE processing_jobs ADD COLUMN IF NOT EXISTS current_step VARCHAR(100) NOT NULL DEFAULT 'queued'")
    op.execute("ALTER TABLE processing_jobs ADD COLUMN IF NOT EXISTS report_id UUID")
    op.execute("ALTER TABLE processing_jobs ADD COLUMN IF NOT EXISTS retry_of_job_id UUID")
    op.execute("ALTER TABLE processing_jobs ADD COLUMN IF NOT EXISTS error_details JSONB")
    op.execute("ALTER TABLE processing_jobs ADD COLUMN IF NOT EXISTS created_by UUID")
    op.execute("ALTER TABLE processing_jobs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()")

    op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS job_id UUID")
    op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS scoring_config_version VARCHAR(100) NOT NULL DEFAULT 'trust-score-v1.0'")
    op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS report_trust_score DOUBLE PRECISION NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS overall_label VARCHAR(50) NOT NULL DEFAULT 'needs_review'")
    op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS report_penalty DOUBLE PRECISION NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS summary JSONB NOT NULL DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS component_summary JSONB NOT NULL DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS citations_payload JSONB NOT NULL DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS warnings JSONB NOT NULL DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()")

    op.execute("ALTER TABLE report_exports ADD COLUMN IF NOT EXISTS format VARCHAR(20) NOT NULL DEFAULT 'pdf'")
    op.execute("ALTER TABLE report_exports ADD COLUMN IF NOT EXISTS storage_path VARCHAR(500)")
    op.execute("ALTER TABLE report_exports ADD COLUMN IF NOT EXISTS created_by UUID")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'report_exports' AND column_name = 'stored_path') THEN
                UPDATE report_exports SET storage_path = stored_path WHERE storage_path IS NULL;
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'audit_logs' AND column_name = 'user_id')
               AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'audit_logs' AND column_name = 'actor_id') THEN
                ALTER TABLE audit_logs RENAME COLUMN user_id TO actor_id;
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'audit_logs' AND column_name = 'resource_type')
               AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'audit_logs' AND column_name = 'object_type') THEN
                ALTER TABLE audit_logs RENAME COLUMN resource_type TO object_type;
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'audit_logs' AND column_name = 'actor_id') THEN
                ALTER TABLE audit_logs ADD COLUMN actor_id UUID;
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'audit_logs' AND column_name = 'object_type') THEN
                ALTER TABLE audit_logs ADD COLUMN object_type VARCHAR(100);
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'audit_logs' AND column_name = 'object_id') THEN
                ALTER TABLE audit_logs ADD COLUMN object_id UUID;
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'audit_logs' AND column_name = 'resource_id') THEN
                UPDATE audit_logs
                SET object_id = resource_id::uuid
                WHERE object_id IS NULL
                  AND resource_id ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'audit_logs' AND column_name = 'details')
               AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'audit_logs' AND column_name = 'details_json') THEN
                ALTER TABLE audit_logs RENAME COLUMN details TO details_json;
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'audit_logs' AND column_name = 'details_json') THEN
                ALTER TABLE audit_logs ADD COLUMN details_json JSONB;
            END IF;

            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'audit_logs' AND column_name = 'message') THEN
                UPDATE audit_logs
                SET details_json = COALESCE(details_json, '{}'::jsonb) || jsonb_build_object('message', message)
                WHERE message IS NOT NULL;
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'audit_logs' AND column_name = 'ip_address') THEN
                ALTER TABLE audit_logs ADD COLUMN ip_address VARCHAR(100);
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'audit_logs' AND column_name = 'user_agent') THEN
                ALTER TABLE audit_logs ADD COLUMN user_agent VARCHAR(500);
            END IF;
        END $$;
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_id ON audit_logs (actor_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_object_id ON audit_logs (object_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_object_id")
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_actor_id")
