"""OpenComputers Tunnels resource — sync and async variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .types import Tunnel, TunnelCreateParams, TunnelListResponse, TunnelUpdateParams

if TYPE_CHECKING:
    from ..._http import AsyncTransport, SyncTransport


class TunnelsResource:
    """Manage HTTP tunnels exposing host ports publicly (sync)."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def _base(self, host_id: str) -> str:
        return f"/opencomputers/hosts/{host_id}/tunnels"

    def list(self, host_id: str) -> TunnelListResponse:
        data = self._transport.request("GET", self._base(host_id))
        return TunnelListResponse.model_validate(data)

    def create(self, host_id: str, params: TunnelCreateParams) -> Tunnel:
        data = self._transport.request(
            "POST", self._base(host_id), json_body=params.model_dump(exclude_none=True)
        )
        return Tunnel.model_validate(data)

    def get(self, host_id: str, tunnel_id: str) -> Tunnel:
        data = self._transport.request("GET", f"{self._base(host_id)}/{tunnel_id}")
        return Tunnel.model_validate(data)

    def update(self, host_id: str, tunnel_id: str, params: TunnelUpdateParams) -> Tunnel:
        data = self._transport.request(
            "PATCH",
            f"{self._base(host_id)}/{tunnel_id}",
            json_body=params.model_dump(exclude_none=True),
        )
        return Tunnel.model_validate(data)

    def delete(self, host_id: str, tunnel_id: str) -> None:
        self._transport.request("DELETE", f"{self._base(host_id)}/{tunnel_id}")


class AsyncTunnelsResource:
    """Manage HTTP tunnels exposing host ports publicly (async)."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    def _base(self, host_id: str) -> str:
        return f"/opencomputers/hosts/{host_id}/tunnels"

    async def list(self, host_id: str) -> TunnelListResponse:
        data = await self._transport.request("GET", self._base(host_id))
        return TunnelListResponse.model_validate(data)

    async def create(self, host_id: str, params: TunnelCreateParams) -> Tunnel:
        data = await self._transport.request(
            "POST", self._base(host_id), json_body=params.model_dump(exclude_none=True)
        )
        return Tunnel.model_validate(data)

    async def get(self, host_id: str, tunnel_id: str) -> Tunnel:
        data = await self._transport.request("GET", f"{self._base(host_id)}/{tunnel_id}")
        return Tunnel.model_validate(data)

    async def update(
        self, host_id: str, tunnel_id: str, params: TunnelUpdateParams
    ) -> Tunnel:
        data = await self._transport.request(
            "PATCH",
            f"{self._base(host_id)}/{tunnel_id}",
            json_body=params.model_dump(exclude_none=True),
        )
        return Tunnel.model_validate(data)

    async def delete(self, host_id: str, tunnel_id: str) -> None:
        await self._transport.request("DELETE", f"{self._base(host_id)}/{tunnel_id}")
