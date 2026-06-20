from typing import Any


AUTH_LOGIN = "auth.login"
COURSE_MANAGE = "course.manage"
ASSIGNMENT_MANAGE = "assignment.manage"
SUBMISSION_UPLOAD = "submission.upload"
JOB_ANALYZE = "job.analyze"
REPORT_VIEW_OWN_SCOPE = "report.view_own_scope"
REPORT_EXPORT = "report.export"
ADMIN_USER_MANAGE = "admin.user_manage"
ADMIN_SCORING_CONFIG = "admin.scoring_config"
ADMIN_AUDIT_LOG = "admin.audit_log"
ADMIN_METADATA_PROVIDER = "admin.metadata_provider"


ROLE_LECTURER = "LECTURER"
ROLE_ADMIN = "ADMIN"
ROLE_STUDENT = "STUDENT"


LECTURER_PERMISSIONS = {
    AUTH_LOGIN,
    COURSE_MANAGE,
    ASSIGNMENT_MANAGE,
    SUBMISSION_UPLOAD,
    JOB_ANALYZE,
    REPORT_VIEW_OWN_SCOPE,
    REPORT_EXPORT,
}

ADMIN_PERMISSIONS = {
    *LECTURER_PERMISSIONS,
    ADMIN_USER_MANAGE,
    ADMIN_SCORING_CONFIG,
    ADMIN_AUDIT_LOG,
    ADMIN_METADATA_PROVIDER,
}

STUDENT_PERMISSIONS = {
    AUTH_LOGIN,
}


ROLE_PERMISSIONS = {
    ROLE_LECTURER: LECTURER_PERMISSIONS,
    ROLE_ADMIN: ADMIN_PERMISSIONS,
    ROLE_STUDENT: STUDENT_PERMISSIONS,
}


ROLE_LABELS = {
    ROLE_LECTURER: "Giảng viên",
    ROLE_ADMIN: "Quản trị viên",
    ROLE_STUDENT: "Sinh viên",
}


def normalize_role(role: Any) -> str:
    return str(role or "").strip().upper()


def get_permissions_for_role(role: Any) -> list[str]:
    normalized_role = normalize_role(role)
    return sorted(ROLE_PERMISSIONS.get(normalized_role, set()))


def has_permission(role: Any, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(normalize_role(role), set())


def has_any_permission(role: Any, permissions: list[str] | tuple[str, ...] | set[str]) -> bool:
    role_permissions = ROLE_PERMISSIONS.get(normalize_role(role), set())
    return any(permission in role_permissions for permission in permissions)


def has_all_permissions(role: Any, permissions: list[str] | tuple[str, ...] | set[str]) -> bool:
    role_permissions = ROLE_PERMISSIONS.get(normalize_role(role), set())
    return all(permission in role_permissions for permission in permissions)
