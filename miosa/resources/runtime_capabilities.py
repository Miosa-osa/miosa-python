"""Runtime capabilities — live backend feature and contract discovery."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any) -> Any:
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data


class RuntimeCapabilities:
    """Fetch the live MIOSA runtime capability contract."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def get(self) -> dict[str, Any]:
        return _unwrap(self._t.request("GET", "/runtime-capabilities"))


class AsyncRuntimeCapabilities:
    """Async Runtime Capabilities API."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def get(self) -> dict[str, Any]:
        return _unwrap(await self._t.request("GET", "/runtime-capabilities"))
