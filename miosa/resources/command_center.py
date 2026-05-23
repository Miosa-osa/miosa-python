"""Command Center — agent fleet, orchestrations, metrics.

Routes live under ``/api/v1/command-center/`` and require a JWT (or
``msk_u_*`` API key). Returns empty/zero data until the Optimal AI
engine read-side API is wired in.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Iterator, List

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(
    data: Any,
    keys: tuple[str, ...] = (
        "data",
        "agents",
        "running",
        "metrics",
        "presets",
        "tiers",
        "items",
    ),
) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class CommandCenter:
    """Read-only views of the Optimal AI agent fleet."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def overview(self) -> Dict[str, Any]:
        """Top-level snapshot (GET ``/command-center``)."""
        return _unwrap(self._t.request("GET", "/command-center"))

    def agents(self) -> List[Dict[str, Any]]:
        data = self._t.request("GET", "/command-center/agents")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def running_agents(self) -> List[Dict[str, Any]]:
        data = self._t.request("GET", "/command-center/agents/running")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def metrics(self) -> Dict[str, Any]:
        return _unwrap(self._t.request("GET", "/command-center/metrics"))

    def presets(self) -> List[Dict[str, Any]]:
        data = self._t.request("GET", "/command-center/presets")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def tiers(self) -> Dict[str, Any]:
        return _unwrap(self._t.request("GET", "/command-center/tiers"))

    def events(self) -> Iterator[Dict[str, Any]]:
        """Stream live command-center events via SSE."""
        return self._t.stream_sse("/command-center/events")


class AsyncCommandCenter:
    """Async command center."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def overview(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", "/command-center"))

    async def agents(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", "/command-center/agents")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def running_agents(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", "/command-center/agents/running")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def metrics(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", "/command-center/metrics"))

    async def presets(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", "/command-center/presets")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def tiers(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", "/command-center/tiers"))

    def events(self):
        """Async-stream live command-center events via SSE."""
        return self._t.stream_sse("/command-center/events")
