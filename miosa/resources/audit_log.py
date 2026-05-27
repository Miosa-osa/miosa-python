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

    def list(
        self,
        *,
        after: Any = None,
        limit: Any = None,
        type: Any = None,
        actor_id: Any = None,
        resource_type: Any = None,
        resource_id: Any = None,
        **filters: Any,
    ) -> List[Dict[str, Any]]:
        """GET /api/v1/audit-log — list audit events.

        Args:
            after: Cursor from the previous page's ``next_cursor``.
            limit: Maximum results to return (default 100).
            type: Filter by event type string.
            actor_id: Filter by actor ID.
            resource_type: Filter by resource type (e.g. ``"sandbox"``).
            resource_id: Filter by resource ID.
        """
        params: Dict[str, Any] = {
            **{k: v for k, v in filters.items() if v is not None},
        }
        for key, value in (
            ("after", after),
            ("limit", limit),
            ("type", type),
            ("actor_id", actor_id),
            ("resource_type", resource_type),
            ("resource_id", resource_id),
        ):
            if value is not None:
                params[key] = value
        data = self._t.request("GET", "/audit-log", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []


class AsyncAuditLog:
    """Async audit log."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(
        self,
        *,
        after: Any = None,
        limit: Any = None,
        type: Any = None,
        actor_id: Any = None,
        resource_type: Any = None,
        resource_id: Any = None,
        **filters: Any,
    ) -> List[Dict[str, Any]]:
        """GET /api/v1/audit-log — list audit events."""
        params: Dict[str, Any] = {
            **{k: v for k, v in filters.items() if v is not None},
        }
        for key, value in (
            ("after", after),
            ("limit", limit),
            ("type", type),
            ("actor_id", actor_id),
            ("resource_type", resource_type),
            ("resource_id", resource_id),
        ):
            if value is not None:
                params[key] = value
        data = await self._t.request("GET", "/audit-log", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []
