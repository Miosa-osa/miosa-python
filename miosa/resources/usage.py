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

    def get(
        self,
        *,
        external_user_id: Optional[str] = None,
        group_by: Optional[str] = None,
        period: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Dict[str, Any]:
        """GET /api/v1/usage — usage rollup per contracts.

        Args:
            external_user_id: Filter results to one white-label user.
            group_by: Dimension to aggregate by. One of ``external_user_id``,
                      ``external_project_id``, ``workspace_id``.
            period: Shorthand period: ``"7d"``, ``"30d"``, ``"month-to-date"``.
            start: ISO timestamp range start (used instead of ``period``).
            end: ISO timestamp range end (used together with ``start``).

        Returns:
            ``{"period_start", "period_end", "results": [...]}``
        """
        params: Dict[str, Any] = {}
        if external_user_id is not None:
            params["external_user_id"] = external_user_id
        if group_by is not None:
            params["group_by"] = group_by
        if period is not None:
            params["period"] = period
        if start is not None:
            params["start"] = start
        if end is not None:
            params["end"] = end
        return _unwrap(self._t.request("GET", "/usage", params=params or None))

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

    async def get(
        self,
        *,
        external_user_id: Optional[str] = None,
        group_by: Optional[str] = None,
        period: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Dict[str, Any]:
        """GET /api/v1/usage — async usage rollup."""
        params: Dict[str, Any] = {}
        if external_user_id is not None:
            params["external_user_id"] = external_user_id
        if group_by is not None:
            params["group_by"] = group_by
        if period is not None:
            params["period"] = period
        if start is not None:
            params["start"] = start
        if end is not None:
            params["end"] = end
        return _unwrap(await self._t.request("GET", "/usage", params=params or None))

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
