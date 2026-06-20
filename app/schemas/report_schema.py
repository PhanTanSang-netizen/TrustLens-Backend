from typing import Any

from pydantic import BaseModel


class ReportSubmissionInfo(BaseModel):
    id: str | None = None
    assignment_id: str | None = None
    file_id: str | None = None
    owner_label: str | None = None
    status: str | None = None
    overall_score: float | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ReportFileInfo(BaseModel):
    id: str | None = None
    original_name: str | None = None
    stored_name: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    checksum: str | None = None
    uploaded_by: str | None = None
    created_at: str | None = None


class ReportExtractedDocumentInfo(BaseModel):
    id: str | None = None
    word_count: int | None = None
    page_count: int | None = None
    extraction_method: str | None = None
    status: str | None = None
    created_at: str | None = None


class ReportReferenceSectionInfo(BaseModel):
    id: str | None = None
    heading: str | None = None
    start_index: int | None = None
    end_index: int | None = None
    detection_method: str | None = None
    raw_text_preview: str | None = None


class ReportLatestJobInfo(BaseModel):
    id: str | None = None
    status: str | None = None
    progress: int | None = None
    step: str | None = None
    error_code: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ReportProcessingSummary(BaseModel):
    submission_status: str | None = None
    has_extracted_text: bool
    has_reference_section: bool
    citation_count: int
    metadata_record_count: int
    latest_job: ReportLatestJobInfo | None = None


class ReportVerificationSummary(BaseModel):
    total: int
    verified: int
    basic_metadata_present: int
    broken: int
    forbidden: int
    unreachable: int
    not_provided: int


class ReportScoreSummary(BaseModel):
    overall_score: float | None = None
    trust_level: str
    note: str | None = None


class ReportSummary(BaseModel):
    processing: ReportProcessingSummary
    verification: ReportVerificationSummary
    score: ReportScoreSummary


class ReportCitationInfo(BaseModel):
    id: str | None = None
    sequence_no: int | None = None
    raw_text: str | None = None
    detected_style: str | None = None
    authors: str | None = None
    title: str | None = None
    year: int | None = None
    doi: str | None = None
    url: str | None = None


class ReportMetadataInfo(BaseModel):
    id: str | None = None
    provider: str | None = None
    query_type: str | None = None
    query_value: str | None = None
    source_url: str | None = None
    matched_title: str | None = None
    matched_year: int | None = None
    verification_status: str | None = None
    confidence_score: float | None = None
    raw_response: dict[str, Any] | None = None


class ReportCitationItem(BaseModel):
    citation: ReportCitationInfo
    metadata: ReportMetadataInfo
    warnings: list[str]
    score: float | None = None
    trust_level: str


class SubmissionReportResponse(BaseModel):
    message: str
    submission: ReportSubmissionInfo
    file: ReportFileInfo | None = None
    extracted_document: ReportExtractedDocumentInfo | None = None
    reference_section: ReportReferenceSectionInfo | None = None
    summary: ReportSummary
    citations: list[ReportCitationItem]
