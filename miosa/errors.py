"""MIOSA SDK exception hierarchy."""

from __future__ import annotations

from typing import Any, Optional, cast


class MiosaError(Exception):
    """Base exception for all MIOSA SDK errors."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
        body: Optional[Any] = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.body = body
        self.request_id = request_id
        self.details = _extract_details(body)

    def __repr__(self) -> str:
        parts = [f"message={self.message!r}"]
        if self.status_code is not None:
            parts.append(f"status_code={self.status_code}")
        if self.code is not None:
            parts.append(f"code={self.code!r}")
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
        code: Optional[str] = None,
        body: Optional[Any] = None,
        request_id: Optional[str] = None,
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            code=code,
            body=body,
            request_id=request_id,
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


class ProjectNotLinkedError(PermissionError):
    """Raised when a connector token request is not linked to the project."""


class SubjectNotAllowedError(PermissionError):
    """Raised when the connector project link does not allow the subject type."""


class ScopeNotAllowedError(PermissionError):
    """Raised when requested provider scopes exceed the connector project link."""


class ManagedProviderBindingOnlyError(PermissionError):
    """Raised when a managed connector can only be bound into a runtime."""


class InstallationRequiredError(MiosaError):
    """Raised when a connector requires an installation/grant first."""


class UserAuthorizationRequiredError(PermissionError):
    """Raised when a user-subject connector request needs user consent."""


class EgressHostNotAllowedError(PermissionError):
    """Raised when runtime egress attempts an unapproved provider host."""


class TokenRefreshFailedError(ServerError):
    """Raised when an OAuth-backed connector cannot refresh a provider token."""


_STATUS_TO_ERROR: dict[int, type[MiosaError]] = {
    401: AuthenticationError,
    402: InsufficientCreditsError,
    403: PermissionError,
    404: NotFoundError,
    422: ValidationError,
    429: RateLimitError,
}

_CODE_TO_ERROR: dict[str, type[MiosaError]] = {
    "PROJECT_NOT_LINKED": ProjectNotLinkedError,
    "SUBJECT_NOT_ALLOWED": SubjectNotAllowedError,
    "SCOPE_NOT_ALLOWED": ScopeNotAllowedError,
    "MANAGED_PROVIDER_BINDING_ONLY": ManagedProviderBindingOnlyError,
    "INSTALLATION_REQUIRED": InstallationRequiredError,
    "USER_AUTHORIZATION_REQUIRED": UserAuthorizationRequiredError,
    "EGRESS_HOST_NOT_ALLOWED": EgressHostNotAllowedError,
    "TOKEN_REFRESH_FAILED": TokenRefreshFailedError,
}


def raise_for_status(
    status_code: int,
    body: Any,
    request_id: Optional[str] = None,
) -> None:
    """Raise the appropriate ``MiosaError`` subclass for a non-2xx response."""
    if 200 <= status_code < 300:
        return

    request_id = request_id or _extract_body_request_id(body)
    code = _extract_code(body)
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
            code=code,
            body=body,
            request_id=request_id,
            retry_after=retry_after,
        )

    error_cls = _CODE_TO_ERROR.get(code or "") or _STATUS_TO_ERROR.get(status_code)
    if error_cls is None:
        error_cls = ServerError if status_code >= 500 else MiosaError

    raise error_cls(
        message,
        status_code=status_code,
        code=code,
        body=body,
        request_id=request_id,
    )


def _extract_request_id(resp: Any) -> str:
    """Extract the X-Request-Id header from an httpx response."""
    if hasattr(resp, "headers"):
        return str(resp.headers.get("x-request-id", ""))
    return ""


def _extract_message(body: Any, status_code: int) -> str:
    """Best-effort extraction of a human-readable error message."""
    if isinstance(body, dict):
        nested = body.get("error")
        if isinstance(nested, dict) and isinstance(nested.get("message"), str):
            return cast(str, nested["message"])
        flat_error = body.get("error")
        if (
            isinstance(flat_error, str)
            and flat_error.replace("_", "").isalnum()
            and flat_error.upper() == flat_error
            and isinstance(body.get("detail"), str)
        ):
            return cast(str, body["detail"])
        for key in ("message", "detail", "reason", "error", "errors"):
            val = body.get(key)
            if isinstance(val, str):
                return val
            if isinstance(val, list) and val:
                return str(val[0])
    if isinstance(body, str) and body:
        return body
    return f"API request failed with status {status_code}"


def _extract_code(body: Any) -> Optional[str]:
    """Best-effort extraction of a stable backend error code."""
    if isinstance(body, dict):
        nested = body.get("error")
        if isinstance(nested, dict) and isinstance(nested.get("code"), str):
            return cast(str, nested["code"])
        code = body.get("code")
        if isinstance(code, str):
            return code
        flat_error = body.get("error")
        if (
            isinstance(flat_error, str)
            and flat_error.replace("_", "").isalnum()
            and flat_error.upper() == flat_error
        ):
            return flat_error
    return None


def _extract_details(body: Any) -> Any:
    if not isinstance(body, dict):
        return None
    nested = body.get("error")
    if isinstance(nested, dict) and "details" in nested:
        return nested["details"]
    if "details" in body:
        return body["details"]
    detail = {key: body[key] for key in ("detail", "reason") if key in body}
    return detail or None


def _extract_body_request_id(body: Any) -> Optional[str]:
    if isinstance(body, dict) and isinstance(body.get("request_id"), str):
        return cast(str, body["request_id"])
    return None
