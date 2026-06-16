from dataclasses import dataclass

import httpx


@dataclass
class UrlCheckResult:
    verification_status: str
    confidence_score: float
    status_code: int | None
    final_url: str | None
    error: str | None


def is_redirected_to_404_page(final_url: str | None) -> bool:
    if not final_url:
        return False

    normalized = final_url.lower()

    return (
        "/404" in normalized
        or "page/404" in normalized
        or "not-found" in normalized
        or "notfound" in normalized
    )


def check_url_exists(url: str | None) -> UrlCheckResult:
    if not url or not url.strip():
        return UrlCheckResult(
            verification_status="URL_NOT_PROVIDED",
            confidence_score=0.0,
            status_code=None,
            final_url=None,
            error="Citation does not contain URL.",
        )

    normalized_url = url.strip()

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=10.0,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36 TrustLens-MVP/1.0"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        ) as client:
            response = client.head(normalized_url)

            if response.status_code in [403, 405] or response.status_code >= 400:
                response = client.get(normalized_url)

            status_code = response.status_code
            final_url = str(response.url)

            if is_redirected_to_404_page(final_url):
                return UrlCheckResult(
                    verification_status="URL_BROKEN",
                    confidence_score=0.15,
                    status_code=status_code,
                    final_url=final_url,
                    error="URL redirected to a 404/not-found page.",
                )

            if status_code == 403:
                return UrlCheckResult(
                    verification_status="URL_FORBIDDEN",
                    confidence_score=0.45,
                    status_code=status_code,
                    final_url=final_url,
                    error="Server returned 403 Forbidden. URL may exist but blocks automated requests.",
                )

            if 200 <= status_code < 400:
                return UrlCheckResult(
                    verification_status="URL_OK",
                    confidence_score=0.70,
                    status_code=status_code,
                    final_url=final_url,
                    error=None,
                )

            if status_code == 404:
                return UrlCheckResult(
                    verification_status="URL_BROKEN",
                    confidence_score=0.10,
                    status_code=status_code,
                    final_url=final_url,
                    error="HTTP status code: 404",
                )

            return UrlCheckResult(
                verification_status="URL_BROKEN",
                confidence_score=0.20,
                status_code=status_code,
                final_url=final_url,
                error=f"HTTP status code: {status_code}",
            )

    except httpx.RequestError as exc:
        return UrlCheckResult(
            verification_status="URL_UNREACHABLE",
            confidence_score=0.20,
            status_code=None,
            final_url=normalized_url,
            error=str(exc),
        )