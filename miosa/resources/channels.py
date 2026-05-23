"""Channels — notification preferences + per-channel enable/disable."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(
    data: Any,
    keys: tuple[str, ...] = ("data", "channels", "notifications", "items"),
) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class Channels:
    """Notification channels — Slack, Discord, email, etc."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        """List all channels for the tenant."""
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request("GET", "/channels", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def get(self, channel_id: str) -> Dict[str, Any]:
        """Get a single channel."""
        return _unwrap(self._t.request("GET", f"/channels/{channel_id}"))

    def create(self, **attrs: Any) -> Dict[str, Any]:
        """Create a new channel."""
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(self._t.request("POST", "/channels", json_body=body))

    def update(self, channel_id: str, **attrs: Any) -> Dict[str, Any]:
        """Update a channel."""
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            self._t.request(
                "PATCH", f"/channels/{channel_id}", json_body=body
            )
        )

    def delete(self, channel_id: str) -> None:
        """Delete a channel."""
        self._t.request("DELETE", f"/channels/{channel_id}")

    # ── Notification preferences ────────────────────────────────────────

    def list_notifications(self) -> Dict[str, Any]:
        """Get notification preferences across all channels."""
        return _unwrap(self._t.request("GET", "/channels/notifications"))

    def update_notifications(self, **prefs: Any) -> Dict[str, Any]:
        """Update notification preferences."""
        body = {k: v for k, v in prefs.items() if v is not None}
        return _unwrap(
            self._t.request("PUT", "/channels/notifications", json_body=body)
        )

    def enable(self, channel_id: str) -> Dict[str, Any]:
        """Enable a channel."""
        return _unwrap(self._t.request("POST", f"/channels/{channel_id}/enable"))

    def disable(self, channel_id: str) -> Dict[str, Any]:
        """Disable a channel."""
        return _unwrap(
            self._t.request("POST", f"/channels/{channel_id}/disable")
        )


class AsyncChannels:
    """Async channels."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request("GET", "/channels", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def get(self, channel_id: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", f"/channels/{channel_id}"))

    async def create(self, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(await self._t.request("POST", "/channels", json_body=body))

    async def update(self, channel_id: str, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            await self._t.request(
                "PATCH", f"/channels/{channel_id}", json_body=body
            )
        )

    async def delete(self, channel_id: str) -> None:
        await self._t.request("DELETE", f"/channels/{channel_id}")

    async def list_notifications(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", "/channels/notifications"))

    async def update_notifications(self, **prefs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in prefs.items() if v is not None}
        return _unwrap(
            await self._t.request(
                "PUT", "/channels/notifications", json_body=body
            )
        )

    async def enable(self, channel_id: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request("POST", f"/channels/{channel_id}/enable")
        )

    async def disable(self, channel_id: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request("POST", f"/channels/{channel_id}/disable")
        )
