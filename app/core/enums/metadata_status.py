from enum import StrEnum


class MetadataStatus(StrEnum):
    VERIFIED = "VERIFIED"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_FOUND = "NOT_FOUND"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    URL_ONLY = "URL_ONLY"
    INVALID_IDENTIFIER = "INVALID_IDENTIFIER"
    IDENTIFIER_METADATA_CONFLICT = "IDENTIFIER_METADATA_CONFLICT"


_LEGACY_STATUS_MAP = {
    "verified": MetadataStatus.VERIFIED,
    "ACADEMIC_VERIFIED": MetadataStatus.VERIFIED,
    "partial": MetadataStatus.PARTIAL_MATCH,
    "ACADEMIC_PARTIAL_MATCH": MetadataStatus.PARTIAL_MATCH,
    "ambiguous": MetadataStatus.AMBIGUOUS,
    "ACADEMIC_AMBIGUOUS": MetadataStatus.AMBIGUOUS,
    "not_found": MetadataStatus.NOT_FOUND,
    "ACADEMIC_NOT_FOUND": MetadataStatus.NOT_FOUND,
    "unknown": MetadataStatus.PROVIDER_UNAVAILABLE,
    "METADATA_NOT_PROVIDED": MetadataStatus.NOT_FOUND,
    "BASIC_METADATA_PRESENT": MetadataStatus.NOT_FOUND,
    "DOI_OK": MetadataStatus.URL_ONLY,
    "URL_OK": MetadataStatus.URL_ONLY,
    "URL_WEAK_EVIDENCE": MetadataStatus.URL_ONLY,
    "URL_FORBIDDEN": MetadataStatus.URL_ONLY,
    "DOI_UNREACHABLE": MetadataStatus.PROVIDER_UNAVAILABLE,
    "URL_UNREACHABLE": MetadataStatus.PROVIDER_UNAVAILABLE,
    "URL_BROKEN": MetadataStatus.NOT_FOUND,
    "URL_NOT_PROVIDED": MetadataStatus.NOT_FOUND,
    "DOI_CONFLICT": MetadataStatus.IDENTIFIER_METADATA_CONFLICT,
}


def normalize_metadata_status(status: str | MetadataStatus | None) -> MetadataStatus:
    if isinstance(status, MetadataStatus):
        return status

    if status is None:
        return MetadataStatus.PROVIDER_UNAVAILABLE

    status_text = str(status).strip()

    if status_text in MetadataStatus.__members__:
        return MetadataStatus[status_text]

    for item in MetadataStatus:
        if status_text == item.value:
            return item

    return _LEGACY_STATUS_MAP.get(status_text, MetadataStatus.PROVIDER_UNAVAILABLE)
