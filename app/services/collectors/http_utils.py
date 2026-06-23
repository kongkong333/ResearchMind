from __future__ import annotations

import json
import socket
import ssl
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


def read_text_url(url: str, *, headers: dict[str, str] | None = None, timeout: int = 30) -> str:
    request = Request(url, headers=headers or {})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except (TimeoutError, socket.timeout) as exc:
        raise RuntimeError(f"Request timed out for {url}: {exc}") from exc
    except URLError as exc:
        if not _is_certificate_verify_failure(exc):
            raise RuntimeError(f"Request failed for {url}: {exc}") from exc
        insecure_context = ssl._create_unverified_context()
        try:
            with urlopen(request, timeout=timeout, context=insecure_context) as response:  # noqa: S310
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except (TimeoutError, socket.timeout) as retry_exc:
            raise RuntimeError(
                f"Request timed out after SSL fallback for {url}: initial={exc}; retry={retry_exc}"
            ) from retry_exc
        except URLError as retry_exc:
            raise RuntimeError(
                f"Request failed after SSL fallback for {url}: initial={exc}; retry={retry_exc}"
            ) from retry_exc


def read_json_url(url: str, *, headers: dict[str, str] | None = None, timeout: int = 30) -> dict[str, Any]:
    return json.loads(read_text_url(url, headers=headers, timeout=timeout))


def _is_certificate_verify_failure(exc: URLError) -> bool:
    reason = getattr(exc, "reason", None)
    if isinstance(reason, ssl.SSLCertVerificationError):
        return True
    return "CERTIFICATE_VERIFY_FAILED" in str(exc) or "certificate verify failed" in str(exc).lower()
