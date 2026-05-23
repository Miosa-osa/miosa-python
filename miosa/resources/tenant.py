"""Tenant — current tenant info and plan/usage."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data", "tenant", "items")) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class Tenant:
    """Tenant info — read the current tenant's plan and usage caps."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def current(self) -> Dict[str, Any]:
        """Get the current tenant's plan, limits, and live usage counters."""
        return _unwrap(self._t.request("GET", "/tenant/plan"))


class AsyncTenant:
    """Async tenant info."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def current(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", "/tenant/plan"))
