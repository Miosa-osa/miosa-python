"""Usage — per-session metering, summary, and reports."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(
    data: Any,
    keys: tuple[str, ...] = ("data", "usage", "sessions", "summary", "items"),
) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class Usage:
    """Usage — current period summary, sessions, and report queries."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def current(self) -> Dict[str, Any]:
        """Get the current period usage summary."""
        return _unwrap(self._t.request("GET", "/usage/summary"))

    def sessions(self, **filters: Any) -> List[Dict[str, Any]]:
        """List per-session metering events."""
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request("GET", "/usage/sessions", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def report(
        self,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
        **filters: Any,
    ) -> Dict[str, Any]:
        """Get a usage report for a period (alias for ``current`` with filters)."""
        params: Dict[str, Any] = {}
        if period_start is not None:
            params["period_start"] = period_start
        if period_end is not None:
            params["period_end"] = period_end
        params.update({k: v for k, v in filters.items() if v is not None})
        return _unwrap(
            self._t.request("GET", "/usage/summary", params=params or None)
        )


class AsyncUsage:
    """Async usage reports."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def current(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", "/usage/summary"))

    async def sessions(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request(
            "GET", "/usage/sessions", params=params or None
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def report(
        self,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
        **filters: Any,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if period_start is not None:
            params["period_start"] = period_start
        if period_end is not None:
            params["period_end"] = period_end
        params.update({k: v for k, v in filters.items() if v is not None})
        return _unwrap(
            await self._t.request(
                "GET", "/usage/summary", params=params or None
            )
        )
