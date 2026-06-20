from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.core.enums.publication_status import PublicationStatus


@dataclass
class PublicationStatusResult:
    publication_status: PublicationStatus
    is_retracted: bool
    retraction_sources: list[dict[str, Any]]
    warnings: list[str]
    checked_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "publication_status": self.publication_status.value,
            "is_retracted": self.is_retracted,
            "retraction_sources": self.retraction_sources,
            "publication_status_warnings": self.warnings,
            "checked_at": self.checked_at,
        }


SEVERITY = {
    PublicationStatus.RETRACTED: 4,
    PublicationStatus.EXPRESSION_OF_CONCERN: 3,
    PublicationStatus.CORRECTED: 2,
    PublicationStatus.ACTIVE_OR_NO_SIGNAL: 1,
    PublicationStatus.UNKNOWN: 0,
}


def evaluate_publication_status(provider: str, raw_response: dict[str, Any] | None, provider_error: str | None = None) -> PublicationStatusResult:
    checked_at = datetime.now(timezone.utc).isoformat()
    if provider_error:
        return PublicationStatusResult(
            publication_status=PublicationStatus.UNKNOWN,
            is_retracted=False,
            retraction_sources=[],
            warnings=["PUBLICATION_STATUS_PROVIDER_UNAVAILABLE"],
            checked_at=checked_at,
        )

    raw = raw_response if isinstance(raw_response, dict) else {}
    provider_name = provider or str(raw.get("provider") or "unknown")
    statuses: list[PublicationStatus] = []
    sources: list[dict[str, Any]] = []
    warnings: list[str] = []

    crossref_status, crossref_sources = _crossref_status(raw, provider_name)
    if crossref_status is not None:
        statuses.append(crossref_status)
        sources.extend(crossref_sources)

    openalex_status, openalex_sources = _openalex_status(raw, provider_name)
    if openalex_status is not None:
        statuses.append(openalex_status)
        sources.extend(openalex_sources)

    if not statuses:
        statuses.append(PublicationStatus.ACTIVE_OR_NO_SIGNAL)

    status = max(statuses, key=lambda item: SEVERITY[item])
    if len({item for item in statuses if item != PublicationStatus.ACTIVE_OR_NO_SIGNAL}) > 1:
        warnings.append("PUBLICATION_STATUS_CONFLICT")

    return PublicationStatusResult(
        publication_status=status,
        is_retracted=status == PublicationStatus.RETRACTED,
        retraction_sources=sources,
        warnings=warnings,
        checked_at=checked_at,
    )


def _crossref_status(raw: dict[str, Any], provider: str) -> tuple[PublicationStatus | None, list[dict[str, Any]]]:
    updates = raw.get("update-to")
    if not isinstance(updates, list):
        return None, []

    sources: list[dict[str, Any]] = []
    strongest: PublicationStatus | None = None
    for update in updates:
        if not isinstance(update, dict):
            continue
        update_type = str(update.get("type") or update.get("update-type") or "").lower()
        label = str(update.get("label") or update.get("source") or "").lower()
        item_status: PublicationStatus | None = None
        if "retract" in update_type or "retract" in label:
            item_status = PublicationStatus.RETRACTED
        elif "concern" in update_type or "concern" in label:
            item_status = PublicationStatus.EXPRESSION_OF_CONCERN
        elif "correct" in update_type or "correct" in label:
            item_status = PublicationStatus.CORRECTED

        if item_status is None:
            continue
        strongest = item_status if strongest is None or SEVERITY[item_status] > SEVERITY[strongest] else strongest
        sources.append(
            {
                "provider": provider or "Crossref",
                "source": update.get("source"),
                "notice_doi": update.get("DOI") or update.get("doi"),
                "date": update.get("updated") or update.get("date"),
                "label": update.get("label") or update.get("type") or update.get("update-type"),
            }
        )

    return strongest, sources


def _openalex_status(raw: dict[str, Any], provider: str) -> tuple[PublicationStatus | None, list[dict[str, Any]]]:
    if "is_retracted" not in raw:
        return None, []
    if raw.get("is_retracted") is True:
        return PublicationStatus.RETRACTED, [{"provider": provider or "OpenAlex", "is_retracted": True}]
    return PublicationStatus.ACTIVE_OR_NO_SIGNAL, [{"provider": provider or "OpenAlex", "is_retracted": False}]
