"""Low-level HTTP transport with auth, retry, and error handling.

Provides both synchronous (``SyncTransport``) and asynchronous
(``AsyncTransport``) transports backed by ``httpx``.
"""

from __future__ import annotations

import asyncio
import json
import random
import time
from typing import Any, Dict, Iterator, Optional, Union

import httpx

from .errors import (
    ConnectionError,
    MiosaError,
    RateLimitError,
    TimeoutError,
    raise_for_status,
)


DEFAULT_BASE_URL = "https://api.miosa.ai/api/v1"
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 3
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_BASE_DELAY = 0.5
_MAX_DELAY = 30.0

# Detect whether HTTP/2 is available. httpx requires the `h2` package (an
# optional extra: ``pip install httpx[http2]``) to negotiate HTTP/2. When
# present we enable it on every client so sequential calls reuse a single
# multiplexed TLS connection and skip the per-call handshake tax. When
# absent we fall back to HTTP/1.1 with keep-alive — still a single reused
# socket, just without multiplexing.
try:  # pragma: no cover — exercised by integration tests
    import h2 as _h2  # noqa: F401

    _HTTP2_AVAILABLE = True
except ImportError:  # pragma: no cover
    _HTTP2_AVAILABLE = False

# Tuned for typical agent workloads: a handful of concurrent in-flight
# requests, mostly sequential within a session.
_DEFAULT_LIMITS = httpx.Limits(
    max_connections=20,
    max_keepalive_connections=20,
    keepalive_expiry=60.0,
)


def _build_headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "miosa-python/0.1.0",
    }


def _parse_body(response: httpx.Response) -> Any:
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            return response.json()
        except (json.JSONDecodeError, ValueError):
            return response.text
    if "image/" in content_type or "application/octet-stream" in content_type:
        return response.content
    return response.text


def _retry_delay(attempt: int, retry_after: Optional[float] = None) -> float:
    if retry_after is not None and retry_after > 0:
        return min(retry_after, _MAX_DELAY)
    delay = _BASE_DELAY * (2 ** attempt) + random.uniform(0, 0.5)
    return min(delay, _MAX_DELAY)


def _extract_request_id(response: httpx.Response) -> Optional[str]:
    return response.headers.get("x-request-id")


# ---------------------------------------------------------------------------
# Sync transport
# ---------------------------------------------------------------------------

class SyncTransport:
    """Synchronous HTTP transport."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        # Singleton httpx.Client per transport instance. The connection
        # pool inside the client is what eliminates the per-call TLS
        # handshake — never instantiate a new client per request.
        self._client = httpx.Client(
            base_url=self._base_url,
            headers=_build_headers(api_key),
            timeout=timeout,
            follow_redirects=True,
            http2=_HTTP2_AVAILABLE,
            limits=_DEFAULT_LIMITS,
        )

    # -- lifecycle --

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SyncTransport":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # -- public api --

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        files: Optional[Any] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        raw_response: bool = False,
    ) -> Any:
        """Send an HTTP request with retry logic.

        Returns parsed JSON body, raw bytes, or the ``httpx.Response``
        when *raw_response* is ``True``.
        """
        last_exc: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.request(
                    method,
                    path,
                    json=json_body,
                    params=_clean_params(params),
                    files=files,
                    data=data,
                    headers=headers,
                )
            except httpx.TimeoutException as exc:
                last_exc = TimeoutError(
                    f"Request timed out: {method} {path}", status_code=None
                )
                if attempt < self._max_retries:
                    time.sleep(_retry_delay(attempt))
                    continue
                raise last_exc from exc
            except httpx.ConnectError as exc:
                last_exc = ConnectionError(
                    f"Connection failed: {method} {path}", status_code=None
                )
                if attempt < self._max_retries:
                    time.sleep(_retry_delay(attempt))
                    continue
                raise last_exc from exc

            if response.status_code in _RETRYABLE_STATUS_CODES and attempt < self._max_retries:
                retry_after = _get_retry_after(response)
                time.sleep(_retry_delay(attempt, retry_after))
                continue

            if raw_response:
                return response

            body = _parse_body(response)
            request_id = _extract_request_id(response)
            raise_for_status(response.status_code, body, request_id)
            return body

        # exhausted retries
        if last_exc is not None:
            raise last_exc
        raise MiosaError("Request failed after retries")

    def stream_sse(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Open an SSE stream and yield parsed events."""
        with self._client.stream(
            "GET",
            path,
            params=_clean_params(params),
            headers={"Accept": "text/event-stream"},
        ) as response:
            if response.status_code != 200:
                body = _parse_body(response)
                raise_for_status(
                    response.status_code, body, _extract_request_id(response)
                )

            event_type: Optional[str] = None
            data_lines: list[str] = []
            event_id: Optional[str] = None

            for raw_line in response.iter_lines():
                line = raw_line

                if not line:
                    # blank line = event dispatch
                    if data_lines:
                        yield {
                            "type": event_type or "message",
                            "data": "\n".join(data_lines),
                            "id": event_id,
                        }
                    event_type = None
                    data_lines = []
                    event_id = None
                    continue

                if line.startswith(":"):
                    continue  # comment

                if line.startswith("event:"):
                    event_type = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[len("data:"):].strip())
                elif line.startswith("id:"):
                    event_id = line[len("id:"):].strip()

            # flush trailing event
            if data_lines:
                yield {
                    "type": event_type or "message",
                    "data": "\n".join(data_lines),
                    "id": event_id,
                }


# ---------------------------------------------------------------------------
# Async transport
# ---------------------------------------------------------------------------

class AsyncTransport:
    """Asynchronous HTTP transport."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        # Singleton httpx.AsyncClient per transport instance — see
        # ``SyncTransport.__init__`` for the rationale.
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=_build_headers(api_key),
            timeout=timeout,
            follow_redirects=True,
            http2=_HTTP2_AVAILABLE,
            limits=_DEFAULT_LIMITS,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncTransport":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        files: Optional[Any] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        raw_response: bool = False,
    ) -> Any:
        last_exc: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.request(
                    method,
                    path,
                    json=json_body,
                    params=_clean_params(params),
                    files=files,
                    data=data,
                    headers=headers,
                )
            except httpx.TimeoutException as exc:
                last_exc = TimeoutError(
                    f"Request timed out: {method} {path}", status_code=None
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(_retry_delay(attempt))
                    continue
                raise last_exc from exc
            except httpx.ConnectError as exc:
                last_exc = ConnectionError(
                    f"Connection failed: {method} {path}", status_code=None
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(_retry_delay(attempt))
                    continue
                raise last_exc from exc

            if response.status_code in _RETRYABLE_STATUS_CODES and attempt < self._max_retries:
                retry_after = _get_retry_after(response)
                await asyncio.sleep(_retry_delay(attempt, retry_after))
                continue

            if raw_response:
                return response

            body = _parse_body(response)
            request_id = _extract_request_id(response)
            raise_for_status(response.status_code, body, request_id)
            return body

        if last_exc is not None:
            raise last_exc
        raise MiosaError("Request failed after retries")

    async def stream_sse(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ):  # -> AsyncIterator[Dict[str, Any]]
        """Open an SSE stream and yield parsed events."""
        async with self._client.stream(
            "GET",
            path,
            params=_clean_params(params),
            headers={"Accept": "text/event-stream"},
        ) as response:
            if response.status_code != 200:
                body = _parse_body(response)
                raise_for_status(
                    response.status_code, body, _extract_request_id(response)
                )

            event_type: Optional[str] = None
            data_lines: list[str] = []
            event_id: Optional[str] = None

            async for raw_line in response.aiter_lines():
                line = raw_line

                if not line:
                    if data_lines:
                        yield {
                            "type": event_type or "message",
                            "data": "\n".join(data_lines),
                            "id": event_id,
                        }
                    event_type = None
                    data_lines = []
                    event_id = None
                    continue

                if line.startswith(":"):
                    continue

                if line.startswith("event:"):
                    event_type = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[len("data:"):].strip())
                elif line.startswith("id:"):
                    event_id = line[len("id:"):].strip()

            if data_lines:
                yield {
                    "type": event_type or "message",
                    "data": "\n".join(data_lines),
                    "id": event_id,
                }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_params(params: Optional[Dict[str, Any]]) -> Optional[Dict[str, Union[str, int, float, bool]]]:
    """Strip ``None`` values from query params."""
    if params is None:
        return None
    return {k: v for k, v in params.items() if v is not None}


def _get_retry_after(response: httpx.Response) -> Optional[float]:
    raw = response.headers.get("retry-after")
    if raw is not None:
        try:
            return float(raw)
        except (ValueError, TypeError):
            pass
    return None
