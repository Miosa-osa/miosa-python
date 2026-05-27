"""Tenant event stream — real-time SSE feed for tenant-level events."""

from __future__ import annotations

import json as _json
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _parse_sse_event(raw_event: Dict[str, Any]) -> Dict[str, Any]:
    """Decode a raw SSE dict ``{event, data, id}`` into a plain payload dict."""
    data_str = raw_event.get("data", "")
    try:
        payload: Any = _json.loads(data_str) if isinstance(data_str, str) else data_str
    except (_json.JSONDecodeError, TypeError):
        payload = {"raw": data_str}
    if not isinstance(payload, dict):
        payload = {"raw": payload}
    payload.setdefault("_event_type", raw_event.get("event", "message"))
    return payload


class TenantEvents:
    """Synchronous tenant event stream — SSE iterator.

    Yields event dicts from ``GET /api/v1/events/stream``.

    Example::

        for event in client.events.stream(types=["sandbox.*", "webhook.delivered"]):
            print(event)
    """

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def stream(
        self,
        *,
        types: Optional[List[str]] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Open an SSE subscription and yield tenant events.

        Args:
            types: Optional list of event type patterns to filter, e.g.
                   ``["sandbox.*", "webhook.delivered"]``.  ``None`` = all events.
        """
        params: Dict[str, Any] = {}
        if types:
            params["types"] = ",".join(types)
        for raw_event in self._t.stream_sse("/events/stream", params=params or None):
            yield _parse_sse_event(raw_event)


class AsyncTenantEvents:
    """Asynchronous tenant event stream."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def stream(
        self,
        *,
        types: Optional[List[str]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Open an async SSE subscription and yield tenant events.

        Args:
            types: Optional list of event type patterns to filter.
        """
        params: Dict[str, Any] = {}
        if types:
            params["types"] = ",".join(types)
        async for raw_event in self._t.stream_sse("/events/stream", params=params or None):
            yield _parse_sse_event(raw_event)
