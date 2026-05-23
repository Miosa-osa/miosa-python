"""Analytics — overview + timeseries (admin scope)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(
    data: Any,
    keys: tuple[str, ...] = ("data", "analytics", "series", "items"),
) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class Analytics:
    """Analytics — admin-scoped overview and timeseries metrics."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def overview(self, **filters: Any) -> Dict[str, Any]:
        """Get the platform analytics overview."""
        params = {k: v for k, v in filters.items() if v is not None}
        return _unwrap(
            self._t.request(
                "GET", "/analytics/overview", params=params or None
            )
        )

    def timeseries(
        self,
        metric: Optional[str] = None,
        period: Optional[str] = None,
        **filters: Any,
    ) -> Dict[str, Any]:
        """Get a timeseries for a metric over a period."""
        params: Dict[str, Any] = {}
        if metric is not None:
            params["metric"] = metric
        if period is not None:
            params["period"] = period
        params.update({k: v for k, v in filters.items() if v is not None})
        return _unwrap(
            self._t.request(
                "GET", "/analytics/timeseries", params=params or None
            )
        )


class AsyncAnalytics:
    """Async analytics."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def overview(self, **filters: Any) -> Dict[str, Any]:
        params = {k: v for k, v in filters.items() if v is not None}
        return _unwrap(
            await self._t.request(
                "GET", "/analytics/overview", params=params or None
            )
        )

    async def timeseries(
        self,
        metric: Optional[str] = None,
        period: Optional[str] = None,
        **filters: Any,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if metric is not None:
            params["metric"] = metric
        if period is not None:
            params["period"] = period
        params.update({k: v for k, v in filters.items() if v is not None})
        return _unwrap(
            await self._t.request(
                "GET", "/analytics/timeseries", params=params or None
            )
        )
