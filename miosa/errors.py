"""MIOSA SDK exception hierarchy."""

from __future__ import annotations

from typing import Any, Optional


class MiosaError(Exception):
    """Base exception for all MIOSA SDK errors."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        body: Optional[Any] = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.body = body
        self.request_id = request_id

    def __repr__(self) -> str:
        parts = [f"message={self.message!r}"]
        if self.status_code is not None:
            parts.append(f"status_code={self.status_code}")
        if self.request_id is not None:
            parts.append(f"request_id={self.request_id!r}")
        return f"{self.__class__.__name__}({', '.join(parts)})"


class AuthenticationError(MiosaError):
    """Raised when the API key is invalid or missing (401)."""


class PermissionError(MiosaError):
    """Raised when the authenticated user lacks access (403)."""


class NotFoundError(MiosaError):
    """Raised when the requested resource does not exist (404)."""


class ValidationError(MiosaError):
    """Raised when the request payload is invalid (422)."""


class RateLimitError(MiosaError):
    """Raised when the API rate limit is exceeded (429).

    Attributes:
        retry_after: Seconds to wait before retrying, if provided by the server.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = 429,
        body: Optional[Any] = None,
        request_id: Optional[str] = None,
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(
            message, status_code=status_code, body=body, request_id=request_id
        )
        self.retry_after = retry_after


class InsufficientCreditsError(MiosaError):
    """Raised when the account has insufficient credits (402)."""


class ServerError(MiosaError):
    """Raised when the API returns a 5xx error."""


class ConnectionError(MiosaError):
    """Raised when the SDK cannot reach the API."""


class TimeoutError(MiosaError):
    """Raised when a request times out."""


_STATUS_TO_ERROR: dict[int, type[MiosaError]] = {
    401: AuthenticationError,
    402: InsufficientCreditsError,
    403: PermissionError,
    404: NotFoundError,
    422: ValidationError,
    429: RateLimitError,
}


def raise_for_status(
    status_code: int,
    body: Any,
    request_id: Optional[str] = None,
) -> None:
    """Raise the appropriate ``MiosaError`` subclass for a non-2xx response."""
    if 200 <= status_code < 300:
        return

    message = _extract_message(body, status_code)

    if status_code == 429:
        retry_after = None
        if isinstance(body, dict):
            raw = body.get("retry_after")
            if raw is not None:
                try:
                    retry_after = float(raw)
                except (ValueError, TypeError):
                    pass
        raise RateLimitError(
            message,
            status_code=status_code,
            body=body,
            request_id=request_id,
            retry_after=retry_after,
        )

    error_cls = _STATUS_TO_ERROR.get(status_code)
    if error_cls is None:
        error_cls = ServerError if status_code >= 500 else MiosaError

    raise error_cls(
        message, status_code=status_code, body=body, request_id=request_id
    )


def _extract_request_id(resp) -> str:
    """Extract the X-Request-Id header from an httpx response."""
    if hasattr(resp, "headers"):
        return resp.headers.get("x-request-id", "")
    return ""


def _extract_message(body: Any, status_code: int) -> str:
    """Best-effort extraction of a human-readable error message."""
    if isinstance(body, dict):
        for key in ("message", "error", "detail", "errors"):
            val = body.get(key)
            if isinstance(val, str):
                return val
            if isinstance(val, list) and val:
                return str(val[0])
    if isinstance(body, str) and body:
        return body
    return f"API request failed with status {status_code}"
