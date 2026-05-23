"""Tenant webhooks — outgoing event delivery."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data", "webhooks", "deliveries", "items")) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class Webhooks:
    """Tenant-level outgoing webhooks — CRUD, test, delivery history."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request("GET", "/webhooks", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def get(self, webhook_id: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("GET", f"/webhooks/{webhook_id}"))

    def create(self, *, url: str, events: List[str], **attrs: Any) -> Dict[str, Any]:
        body = {
            "url": url,
            "events": events,
            **{k: v for k, v in attrs.items() if v is not None},
        }
        return _unwrap(self._t.request("POST", "/webhooks", json_body=body))

    def update(self, webhook_id: str, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            self._t.request("PATCH", f"/webhooks/{webhook_id}", json_body=body)
        )

    def delete(self, webhook_id: str) -> None:
        self._t.request("DELETE", f"/webhooks/{webhook_id}")

    def test(self, webhook_id: str) -> Dict[str, Any]:
        """Send a test event to verify the webhook endpoint."""
        return _unwrap(self._t.request("POST", f"/webhooks/{webhook_id}/test"))

    def deliveries(self, webhook_id: str) -> List[Dict[str, Any]]:
        """List recent delivery attempts for a webhook."""
        data = self._t.request("GET", f"/webhooks/{webhook_id}/deliveries")
        result = _unwrap(data)
        return result if isinstance(result, list) else []


class AsyncWebhooks:
    """Async tenant webhooks."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request("GET", "/webhooks", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def get(self, webhook_id: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", f"/webhooks/{webhook_id}"))

    async def create(self, *, url: str, events: List[str], **attrs: Any) -> Dict[str, Any]:
        body = {
            "url": url,
            "events": events,
            **{k: v for k, v in attrs.items() if v is not None},
        }
        return _unwrap(await self._t.request("POST", "/webhooks", json_body=body))

    async def update(self, webhook_id: str, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            await self._t.request("PATCH", f"/webhooks/{webhook_id}", json_body=body)
        )

    async def delete(self, webhook_id: str) -> None:
        await self._t.request("DELETE", f"/webhooks/{webhook_id}")

    async def test(self, webhook_id: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("POST", f"/webhooks/{webhook_id}/test"))

    async def deliveries(self, webhook_id: str) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", f"/webhooks/{webhook_id}/deliveries")
        result = _unwrap(data)
        return result if isinstance(result, list) else []
