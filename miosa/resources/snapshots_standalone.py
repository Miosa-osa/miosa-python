"""Snapshots (standalone) — fleet-wide snapshot index for admin callers.

Routes live under ``/api/v1/admin/snapshots/`` and require an admin
credential. Per-computer snapshots remain nested under
``client.computers.get(id).snapshots`` — this resource exposes the
fleet-wide read-only index used by the platform admin dashboard.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(
    data: Any, keys: tuple[str, ...] = ("data", "snapshots", "items")
) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class SnapshotsStandalone:
    """Admin: fleet-wide snapshot index."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request(
            "GET", "/admin/snapshots", params=params or None
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def get(self, snapshot_id: str) -> Dict[str, Any]:
        return _unwrap(
            self._t.request("GET", f"/admin/snapshots/{snapshot_id}")
        )


class AsyncSnapshotsStandalone:
    """Async fleet-wide snapshot index."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request(
            "GET", "/admin/snapshots", params=params or None
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def get(self, snapshot_id: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request("GET", f"/admin/snapshots/{snapshot_id}")
        )
