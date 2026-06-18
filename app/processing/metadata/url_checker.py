from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx


@dataclass
class UrlCheckResult:
    verification_status: str
    confidence_score: float
    status_code: int | None
    final_url: str | None
    error: str | None


GENERIC_PATHS = {
    "",
    "/",
    "home",
    "index",
    "index.html",
    "index.php",
    "trang-chu",
    "homepage",
}


def is_redirected_to_404_page(final_url: str | None) -> bool:
    if not final_url:
        return False

    normalized = final_url.lower()

    return (
        "/404" in normalized
        or "page/404" in normalized
        or "not-found" in normalized
        or "notfound" in normalized
        or "error404" in normalized
    )


def is_weak_evidence_url(
    original_url: str | None,
    final_url: str | None,
) -> bool:
    """
    URL yếu = URL truy cập được nhưng quá chung chung.
    Ví dụ:
    - https://hcma.vn
    - https://tapchicongsan.org.vn
    - https://example.com/
    
    Các URL có path cụ thể hoặc query định danh thì không xem là yếu:
    - /Pages/chi-tiet-tin.aspx?ItemID=117
    - /handle/VNU_123/60415
    - /ark:/48223/pf0000076995
    - /doc/file-name.html
    """

    checked_url = final_url or original_url

    if not checked_url:
        return True

    parts = urlsplit(checked_url)
    path = parts.path.strip().strip("/").lower()
    query = parts.query.strip()

    if path in GENERIC_PATHS and not query:
        return True

    # URL chỉ có domain + query rỗng thường là trang chủ.
    if not path and not query:
        return True

    # URL dạng chuyên mục chung, chưa chỉ rõ bài/tài liệu.
    generic_section_paths = {
        "tin-tuc",
        "bai-viet",
        "van-ban",
        "tai-lieu",
        "document",
        "documents",
        "article",
        "articles",
        "category",
        "chuyen-muc",
    }

    if path in generic_section_paths and not query:
        return True

    return False


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
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "application/pdf,*/*;q=0.8"
                ),
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
                    error=(
                        "Server returned 403 Forbidden. "
                        "URL may exist but blocks automated requests."
                    ),
                )

            if 200 <= status_code < 400:
                if is_weak_evidence_url(
                    original_url=normalized_url,
                    final_url=final_url,
                ):
                    return UrlCheckResult(
                        verification_status="URL_WEAK_EVIDENCE",
                        confidence_score=0.35,
                        status_code=status_code,
                        final_url=final_url,
                        error=(
                            "URL is reachable but too general to verify a specific citation."
                        ),
                    )

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