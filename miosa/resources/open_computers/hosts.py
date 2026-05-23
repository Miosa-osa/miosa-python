"""OpenComputers Hosts resource — sync and async variants."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING

from .types import Host, HostCreateParams, HostEvent, HostListResponse, HostUpdateParams

if TYPE_CHECKING:
    from ..._http import AsyncTransport, SyncTransport


class HostsResource:
    """Manage BYOC hosts registered under the tenant (sync)."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def list(self) -> HostListResponse:
        """List all registered hosts."""
        data = self._transport.request("GET", "/opencomputers/hosts")
        return HostListResponse.model_validate(data)

    def create(self, params: HostCreateParams) -> Host:
        """Register a new host. ``host_key`` in the response is shown once — save it."""
        data = self._transport.request(
            "POST", "/opencomputers/hosts", json_body=params.model_dump(exclude_none=True)
        )
        return Host.model_validate(data)

    def get(self, host_id: str) -> Host:
        """Fetch a host by ID."""
        data = self._transport.request("GET", f"/opencomputers/hosts/{host_id}")
        return Host.model_validate(data)

    def update(self, host_id: str, params: HostUpdateParams) -> Host:
        """Update host name or labels."""
        data = self._transport.request(
            "PATCH",
            f"/opencomputers/hosts/{host_id}",
            json_body=params.model_dump(exclude_none=True),
        )
        return Host.model_validate(data)

    def revoke(self, host_id: str) -> None:
        """Permanently revoke a host — invalidates the host key."""
        self._transport.request("DELETE", f"/opencomputers/hosts/{host_id}")

    def events(self) -> Iterator[HostEvent]:
        """Iterate over host state-change SSE events (blocking generator)."""
        for raw in self._transport.stream_sse("/opencomputers/hosts/events"):
            yield HostEvent.model_validate(raw)


class AsyncHostsResource:
    """Manage BYOC hosts registered under the tenant (async)."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def list(self) -> HostListResponse:
        data = await self._transport.request("GET", "/opencomputers/hosts")
        return HostListResponse.model_validate(data)

    async def create(self, params: HostCreateParams) -> Host:
        data = await self._transport.request(
            "POST", "/opencomputers/hosts", json_body=params.model_dump(exclude_none=True)
        )
        return Host.model_validate(data)

    async def get(self, host_id: str) -> Host:
        data = await self._transport.request("GET", f"/opencomputers/hosts/{host_id}")
        return Host.model_validate(data)

    async def update(self, host_id: str, params: HostUpdateParams) -> Host:
        data = await self._transport.request(
            "PATCH",
            f"/opencomputers/hosts/{host_id}",
            json_body=params.model_dump(exclude_none=True),
        )
        return Host.model_validate(data)

    async def revoke(self, host_id: str) -> None:
        await self._transport.request("DELETE", f"/opencomputers/hosts/{host_id}")

    async def events(self) -> AsyncIterator[HostEvent]:
        async for raw in self._transport.stream_sse("/opencomputers/hosts/events"):
            yield HostEvent.model_validate(raw)
