from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class SubmissionReportResponse(BaseModel):
    report_id: UUID
    submission_id: UUID
    job_id: UUID | None = None
    scoring_config_version: str
    scoring_preset_name: str | None = None
    scoring_preset_code: str | None = None
    scoring_preset_version: int | None = None
    trust_score: dict[str, Any] | None = None
    revision_number: int | None = None
    report_trust_score: float
    confidence_score: float
    overall_label: str
    summary: dict[str, Any]
    report_penalty: dict[str, Any]
    component_summary: dict[str, Any]
    citations: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    created_at: datetime


class ReportHistoryItem(BaseModel):
    id: UUID
    revision_number: int
    report_trust_score: float
    created_at: datetime
