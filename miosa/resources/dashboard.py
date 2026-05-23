"""Dashboard — aggregated platform overview."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(
    data: Any,
    keys: tuple[str, ...] = ("data", "dashboard", "overview", "items"),
) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class Dashboard:
    """Dashboard summary — aggregated platform overview, polled on login."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def summary(self) -> Dict[str, Any]:
        """Aggregated user dashboard payload."""
        return _unwrap(self._t.request("GET", "/dashboard"))

    def overview(self) -> Dict[str, Any]:
        """Status / health overview (public endpoint)."""
        return _unwrap(self._t.request("GET", "/overview"))


class AsyncDashboard:
    """Async dashboard."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def summary(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", "/dashboard"))

    async def overview(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", "/overview"))
