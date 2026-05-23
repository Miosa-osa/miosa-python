"""Audit log — admin-scoped event history."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(
    data: Any,
    keys: tuple[str, ...] = ("data", "audit_log", "events", "items"),
) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class AuditLog:
    """Audit log — admin-scoped event stream."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        """List audit-log events with optional filters."""
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request("GET", "/audit-log", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []


class AsyncAuditLog:
    """Async audit log."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request("GET", "/audit-log", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []
