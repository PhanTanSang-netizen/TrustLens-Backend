"""add p0 mvp runtime tables

Revision ID: d4e5f6a7b8c9
Revises: bc6764b587e6
Create Date: 2026-06-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "bc6764b587e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("processing_jobs", sa.Column("current_step", sa.String(length=100), server_default="queued", nullable=False))
    op.add_column("processing_jobs", sa.Column("report_id", sa.UUID(), nullable=True))
    op.add_column("processing_jobs", sa.Column("retry_of_job_id", sa.UUID(), nullable=True))
    op.add_column("processing_jobs", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("processing_jobs", sa.Column("error_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("processing_jobs", sa.Column("created_by", sa.UUID(), nullable=True))
    op.add_column("processing_jobs", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.create_foreign_key("fk_processing_jobs_retry_of_job_id", "processing_jobs", "processing_jobs", ["retry_of_job_id"], ["id"])
    op.create_foreign_key("fk_processing_jobs_created_by", "processing_jobs", "users", ["created_by"], ["id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("submission_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=True),
        sa.Column("scoring_config_version", sa.String(length=100), nullable=False, server_default="trust-score-v1.0"),
        sa.Column("report_trust_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("overall_label", sa.String(length=50), nullable=False, server_default="needs_review"),
        sa.Column("report_penalty", sa.Float(), nullable=False, server_default="0"),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("component_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("citations_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["processing_jobs.id"]),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reports_job_id"), "reports", ["job_id"], unique=False)
    op.create_index(op.f("ix_reports_submission_id"), "reports", ["submission_id"], unique=True)

    op.create_table(
        "report_exports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("report_id", sa.UUID(), nullable=False),
        sa.Column("format", sa.String(length=20), nullable=False, server_default="pdf"),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="completed"),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_report_exports_report_id"), "report_exports", ["report_id"], unique=False)

    op.create_table(
        "citation_scores",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("citation_id", sa.UUID(), nullable=False),
        sa.Column("scoring_config_version", sa.String(length=100), nullable=False, server_default="trust-score-v1.0"),
        sa.Column("c1", sa.Float(), nullable=False, server_default="0"),
        sa.Column("c2", sa.Float(), nullable=False, server_default="0"),
        sa.Column("c3", sa.Float(), nullable=False, server_default="0"),
        sa.Column("c4", sa.Float(), nullable=False, server_default="0"),
        sa.Column("c5", sa.Float(), nullable=False, server_default="0"),
        sa.Column("c6", sa.Float(), nullable=False, server_default="0"),
        sa.Column("c7", sa.Float(), nullable=False, server_default="0"),
        sa.Column("c8", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reference_trust_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("explanations", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["citation_id"], ["citations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_citation_scores_citation_id"), "citation_scores", ["citation_id"], unique=True)

    op.create_table(
        "warnings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("submission_id", sa.UUID(), nullable=False),
        sa.Column("citation_id", sa.UUID(), nullable=True),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=30), nullable=False, server_default="medium"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["citation_id"], ["citations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_warnings_citation_id"), "warnings", ["citation_id"], unique=False)
    op.create_index(op.f("ix_warnings_submission_id"), "warnings", ["submission_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=True),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False)

    op.create_table(
        "metadata_providers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="healthy"),
        sa.Column("latency", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fallback_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_failure", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_metadata_providers_code"), "metadata_providers", ["code"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_metadata_providers_code"), table_name="metadata_providers")
    op.drop_table("metadata_providers")
    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_warnings_submission_id"), table_name="warnings")
    op.drop_index(op.f("ix_warnings_citation_id"), table_name="warnings")
    op.drop_table("warnings")
    op.drop_index(op.f("ix_citation_scores_citation_id"), table_name="citation_scores")
    op.drop_table("citation_scores")
    op.drop_index(op.f("ix_report_exports_report_id"), table_name="report_exports")
    op.drop_table("report_exports")
    op.drop_index(op.f("ix_reports_submission_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_job_id"), table_name="reports")
    op.drop_table("reports")
    op.drop_constraint("fk_processing_jobs_created_by", "processing_jobs", type_="foreignkey")
    op.drop_constraint("fk_processing_jobs_retry_of_job_id", "processing_jobs", type_="foreignkey")
    op.drop_column("processing_jobs", "updated_at")
    op.drop_column("processing_jobs", "created_by")
    op.drop_column("processing_jobs", "error_details")
    op.drop_column("processing_jobs", "error_message")
    op.drop_column("processing_jobs", "retry_of_job_id")
    op.drop_column("processing_jobs", "report_id")
    op.drop_column("processing_jobs", "current_step")
