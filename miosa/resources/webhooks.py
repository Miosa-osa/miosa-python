"""Tenant webhooks — outgoing event delivery."""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data", "webhooks", "deliveries", "items")) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


def verify_signature(
    body: bytes | bytearray | memoryview | str,
    header: str,
    secret: str,
    tolerance_sec: int = 300,
) -> bool:
    """Verify a MIOSA webhook signature header.

    Current deliveries use ``sha256=<hex_hmac>`` over the raw body.
    Timestamped ``t=<unix_seconds>,v1=<hex_hmac>`` signatures remain accepted
    for compatibility with earlier SDK documentation.
    """
    if isinstance(body, str):
        raw_body = body.encode("utf-8")
    else:
        raw_body = bytes(body)

    if header.startswith("sha256="):
        received = header.removeprefix("sha256=")
        if not received or not secret:
            return False
        expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, received)

    parts: dict[str, str] = {}
    for chunk in header.split(","):
        key, sep, value = chunk.partition("=")
        if sep and key and value:
            parts[key] = value

    timestamp = parts.get("t")
    received = parts.get("v1")
    if not timestamp or not received or not secret:
        return False

    try:
        unix_seconds = int(timestamp)
    except ValueError:
        return False

    if abs(time.time() - unix_seconds) > tolerance_sec:
        raise ValueError("webhook timestamp too old")

    signed = timestamp.encode("utf-8") + b"." + raw_body
    expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received)


class Webhooks:
    """Tenant-level outgoing webhooks — CRUD, test, delivery history."""

    verify_signature = staticmethod(verify_signature)

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def list(self, **filters: Any) -> list[dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request("GET", "/webhooks", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def get(self, webhook_id: str) -> dict[str, Any]:
        return _unwrap(self._t.request("GET", f"/webhooks/{webhook_id}"))

    def create(self, *, url: str, events: list[str], **attrs: Any) -> dict[str, Any]:
        body = {
            "url": url,
            "events": events,
            **{k: v for k, v in attrs.items() if v is not None},
        }
        return _unwrap(self._t.request("POST", "/webhooks", json_body=body))

    def update(self, webhook_id: str, **attrs: Any) -> dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(self._t.request("PATCH", f"/webhooks/{webhook_id}", json_body=body))

    def delete(self, webhook_id: str) -> None:
        self._t.request("DELETE", f"/webhooks/{webhook_id}")

    def test(self, webhook_id: str) -> dict[str, Any]:
        """Send a test event to verify the webhook endpoint."""
        return _unwrap(self._t.request("POST", f"/webhooks/{webhook_id}/test"))

    def deliveries(self, webhook_id: str) -> list[dict[str, Any]]:
        """List recent delivery attempts for a webhook."""
        data = self._t.request("GET", f"/webhooks/{webhook_id}/deliveries")
        result = _unwrap(data)
        return result if isinstance(result, list) else []


class AsyncWebhooks:
    """Async tenant webhooks."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def list(self, **filters: Any) -> list[dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request("GET", "/webhooks", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def get(self, webhook_id: str) -> dict[str, Any]:
        return _unwrap(await self._t.request("GET", f"/webhooks/{webhook_id}"))

    async def create(self, *, url: str, events: list[str], **attrs: Any) -> dict[str, Any]:
        body = {
            "url": url,
            "events": events,
            **{k: v for k, v in attrs.items() if v is not None},
        }
        return _unwrap(await self._t.request("POST", "/webhooks", json_body=body))

    async def update(self, webhook_id: str, **attrs: Any) -> dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(await self._t.request("PATCH", f"/webhooks/{webhook_id}", json_body=body))

    async def delete(self, webhook_id: str) -> None:
        await self._t.request("DELETE", f"/webhooks/{webhook_id}")

    async def test(self, webhook_id: str) -> dict[str, Any]:
        return _unwrap(await self._t.request("POST", f"/webhooks/{webhook_id}/test"))

    async def deliveries(self, webhook_id: str) -> list[dict[str, Any]]:
        data = await self._t.request("GET", f"/webhooks/{webhook_id}/deliveries")
        result = _unwrap(data)
        return result if isinstance(result, list) else []
