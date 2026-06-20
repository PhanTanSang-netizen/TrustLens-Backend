from app.models.user import User
from app.models.role_permission import RolePermission
from app.models.course import Course
from app.models.class_model import ClassModel
from app.models.assignment import Assignment
from app.models.student import Student
from app.models.term import Term
from app.models.file import File
from app.models.submission import Submission
from app.models.processing_job import ProcessingJob
from app.models.extracted_document import ExtractedDocument
from app.models.reference_section import ReferenceSection
from app.models.citation import Citation
from app.models.citation_field import CitationField
from app.models.metadata_provider import MetadataProvider
from app.models.metadata_record import MetadataRecord
from app.models.score_component import ScoreComponent
from app.models.trust_score import TrustScore, CitationScore
from app.models.warning import Warning
from app.models.report import Report, ReportExport
from app.models.scoring_config import ScoringConfig
from app.models.audit_log import AuditLog

__all__ = [
    "User",
    "RolePermission",
    "Course",
    "ClassModel",
    "Assignment",
    "Student",
    "Term",
    "File",
    "Submission",
    "ProcessingJob",
    "ExtractedDocument",
    "ReferenceSection",
    "Citation",
    "CitationField",
    "MetadataProvider",
    "MetadataRecord",
    "ScoreComponent",
    "TrustScore",
    "Warning",
    "Report",
    "ScoringConfig",
    "AuditLog",
    "ReportExport",
    "CitationScore",
    "ensure_user_is_admin",
    "ensure_user_is_lecturer_or_admin",
    "ensure_user_is_student_lecturer_or_admin",
]