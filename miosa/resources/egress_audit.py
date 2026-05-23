"""Egress audit log — paginated query + live tail.

Backed by ``/api/v1/egress/audit`` and ``/api/v1/egress/audit/:id``.

``client.audit.tail()`` long-polls the REST endpoint and yields new
events as they arrive. The sandbox-scoped variant
(``sandbox.audit.tail()``) upgrades to a live SSE/WebSocket connection
backed by ``GET /sandboxes/:id/audit/stream`` so the tail latency is
sub-second.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


_AUDIT_PATH = "/egress/audit"


def _unwrap(data: Any, keys: tuple[str, ...] = ("data", "event", "items")) -> Any:
    if isinstance(data, dict):
        for key in keys:
            if key in data and len(data) <= 2:
                return data[key]
    return data


def _unwrap_list(data: Any, keys: tuple[str, ...] = ("data", "events", "audit", "items")) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return cast(List[Dict[str, Any]], data)
    if isinstance(data, dict):
        for key in keys:
            items = data.get(key)
            if isinstance(items, list):
                return cast(List[Dict[str, Any]], items)
    return []


def _strip_none(body: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in body.items() if v is not None}


# ---------------------------------------------------------------------------
# Sync — tenant-wide
# ---------------------------------------------------------------------------


class EgressAudit:
    """Tenant-wide egress audit log."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def list(
        self,
        *,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        host: Optional[str] = None,
        action: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_workspace_id: Optional[str] = None,
        **filters: Any,
    ) -> List[Dict[str, Any]]:
        """List audit events with optional filters."""
        params = _strip_none({
            "resource_id": resource_id,
            "resource_type": resource_type,
            "host": host,
            "action": action,
            "since": since,
            "until": until,
            "limit": limit,
            "cursor": cursor,
            "external_user_id": external_user_id,
            "external_workspace_id": external_workspace_id,
            **filters,
        })
        data = self._t.request("GET", _AUDIT_PATH, params=params or None)
        return _unwrap_list(data)

    def get(self, event_id: str) -> Dict[str, Any]:
        data = self._t.request("GET", f"{_AUDIT_PATH}/{event_id}")
        return cast(Dict[str, Any], _unwrap(data))

    def tail(
        self,
        *,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        host: Optional[str] = None,
        action: Optional[str] = None,
        poll_interval: float = 2.0,
        **filters: Any,
    ) -> Iterator[Dict[str, Any]]:
        """Long-poll the audit endpoint and yield new events as they appear.

        Note: tenant-wide ``client.audit.tail()`` is REST-based long
        polling. A live WebSocket tail is only available for the
        sandbox-scoped variant (``sandbox.audit.tail()``).
        """
        since: Optional[str] = filters.pop("since", None)
        seen_ids: set[str] = set()
        while True:
            params = _strip_none({
                "resource_id": resource_id,
                "resource_type": resource_type,
                "host": host,
                "action": action,
                "since": since,
                **filters,
            })
            data = self._t.request("GET", _AUDIT_PATH, params=params or None)
            events = _unwrap_list(data)
            new_since = since
            for event in events:
                eid = event.get("id")
                if eid and eid in seen_ids:
                    continue
                if eid:
                    seen_ids.add(str(eid))
                yield event
                ts = event.get("inserted_at") or event.get("timestamp")
                if isinstance(ts, str):
                    new_since = ts
            since = new_since
            time.sleep(poll_interval)


# ---------------------------------------------------------------------------
# Async — tenant-wide
# ---------------------------------------------------------------------------


class AsyncEgressAudit:
    """Asynchronous tenant-wide egress audit log."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def list(
        self,
        *,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        host: Optional[str] = None,
        action: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_workspace_id: Optional[str] = None,
        **filters: Any,
    ) -> List[Dict[str, Any]]:
        params = _strip_none({
            "resource_id": resource_id,
            "resource_type": resource_type,
            "host": host,
            "action": action,
            "since": since,
            "until": until,
            "limit": limit,
            "cursor": cursor,
            "external_user_id": external_user_id,
            "external_workspace_id": external_workspace_id,
            **filters,
        })
        data = await self._t.request("GET", _AUDIT_PATH, params=params or None)
        return _unwrap_list(data)

    async def get(self, event_id: str) -> Dict[str, Any]:
        data = await self._t.request("GET", f"{_AUDIT_PATH}/{event_id}")
        return cast(Dict[str, Any], _unwrap(data))

    async def tail(
        self,
        *,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        host: Optional[str] = None,
        action: Optional[str] = None,
        poll_interval: float = 2.0,
        **filters: Any,
    ) -> AsyncIterator[Dict[str, Any]]:
        since: Optional[str] = filters.pop("since", None)
        seen_ids: set[str] = set()
        while True:
            params = _strip_none({
                "resource_id": resource_id,
                "resource_type": resource_type,
                "host": host,
                "action": action,
                "since": since,
                **filters,
            })
            data = await self._t.request("GET", _AUDIT_PATH, params=params or None)
            events = _unwrap_list(data)
            new_since = since
            for event in events:
                eid = event.get("id")
                if eid and eid in seen_ids:
                    continue
                if eid:
                    seen_ids.add(str(eid))
                yield event
                ts = event.get("inserted_at") or event.get("timestamp")
                if isinstance(ts, str):
                    new_since = ts
            since = new_since
            await asyncio.sleep(poll_interval)


# ---------------------------------------------------------------------------
# Bound — sandbox/computer-scoped wrappers
# ---------------------------------------------------------------------------


class SandboxAudit:
    """Sandbox-bound audit namespace.

    ``list()`` calls the tenant audit endpoint with ``resource_id`` and
    ``resource_type="sandbox"`` pre-filled. ``tail()`` upgrades to the
    per-sandbox SSE stream (``GET /sandboxes/:id/audit/stream``) for
    sub-second tail latency.
    """

    _resource_type: str = "sandbox"

    def __init__(self, transport: SyncTransport, resource_id: str) -> None:
        self._t = transport
        self._resource_id = resource_id
        self._delegate = EgressAudit(transport)

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        filters.setdefault("resource_id", self._resource_id)
        filters.setdefault("resource_type", self._resource_type)
        return self._delegate.list(**filters)

    def get(self, event_id: str) -> Dict[str, Any]:
        return self._delegate.get(event_id)

    def tail(self, **filters: Any) -> Iterator[Dict[str, Any]]:
        """SSE tail of the sandbox-scoped audit stream."""
        params = _strip_none({**filters})
        # Use the bound SSE endpoint on /sandboxes/:id/audit/stream
        stream_path = (
            f"/sandboxes/{self._resource_id}/audit/stream"
            if self._resource_type == "sandbox"
            else f"/computers/{self._resource_id}/audit/stream"
        )
        try:
            for raw in self._t.stream_sse(stream_path, params=params or None):
                payload = raw.get("data") if isinstance(raw, dict) else raw
                if isinstance(payload, str):
                    import json
                    try:
                        yield json.loads(payload)
                    except json.JSONDecodeError:
                        yield {"raw": payload, "type": raw.get("type") if isinstance(raw, dict) else "message"}
                elif isinstance(payload, dict):
                    yield payload
        except Exception:
            # SSE endpoint unavailable — fall back to delegate long-poll.
            yield from self._delegate.tail(
                resource_id=self._resource_id,
                resource_type=self._resource_type,
                **filters,
            )


class AsyncSandboxAudit:
    """Async sandbox-bound audit namespace."""

    _resource_type: str = "sandbox"

    def __init__(self, transport: AsyncTransport, resource_id: str) -> None:
        self._t = transport
        self._resource_id = resource_id
        self._delegate = AsyncEgressAudit(transport)

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        filters.setdefault("resource_id", self._resource_id)
        filters.setdefault("resource_type", self._resource_type)
        return await self._delegate.list(**filters)

    async def get(self, event_id: str) -> Dict[str, Any]:
        return await self._delegate.get(event_id)

    async def tail(self, **filters: Any) -> AsyncIterator[Dict[str, Any]]:
        params = _strip_none({**filters})
        stream_path = (
            f"/sandboxes/{self._resource_id}/audit/stream"
            if self._resource_type == "sandbox"
            else f"/computers/{self._resource_id}/audit/stream"
        )
        try:
            async for raw in self._t.stream_sse(stream_path, params=params or None):
                payload = raw.get("data") if isinstance(raw, dict) else raw
                if isinstance(payload, str):
                    import json
                    try:
                        yield json.loads(payload)
                    except json.JSONDecodeError:
                        yield {"raw": payload, "type": raw.get("type") if isinstance(raw, dict) else "message"}
                elif isinstance(payload, dict):
                    yield payload
        except Exception:
            async for event in self._delegate.tail(
                resource_id=self._resource_id,
                resource_type=self._resource_type,
                **filters,
            ):
                yield event


class ComputerAudit(SandboxAudit):
    """Computer-bound audit namespace."""

    _resource_type = "computer"


class AsyncComputerAudit(AsyncSandboxAudit):
    """Async computer-bound audit namespace."""

    _resource_type = "computer"


__all__ = [
    "AsyncComputerAudit",
    "AsyncEgressAudit",
    "AsyncSandboxAudit",
    "ComputerAudit",
    "EgressAudit",
    "SandboxAudit",
]
