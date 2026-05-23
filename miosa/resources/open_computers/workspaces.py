"""OpenComputers Workspaces resource — sync and async variants."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING

from .types import (
    OcWorkspace,
    OcWorkspaceCreateParams,
    OcWorkspaceEvent,
    OcWorkspaceListResponse,
    OcWorkspaceUpdateParams,
    WsTicket,
)

if TYPE_CHECKING:
    from ..._http import AsyncTransport, SyncTransport


def _parse_ws_event(raw: dict) -> OcWorkspaceEvent:
    data = raw.get("data", "")
    try:
        parsed = json.loads(data) if isinstance(data, str) and data else {}
    except (json.JSONDecodeError, ValueError):
        parsed = {"raw": data}
    return OcWorkspaceEvent.model_validate(parsed)


class OcWorkspacesResource:
    """Git-backed workspace environments on a remote host (sync)."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def list_all(self) -> OcWorkspaceListResponse:
        """List workspaces across all hosts for the tenant."""
        data = self._transport.request("GET", "/opencomputers/workspaces")
        return OcWorkspaceListResponse.model_validate(data)

    def list(self, host_id: str) -> OcWorkspaceListResponse:
        """List workspaces on a specific host."""
        data = self._transport.request("GET", f"/opencomputers/hosts/{host_id}/workspaces")
        return OcWorkspaceListResponse.model_validate(data)

    def create(self, host_id: str, params: OcWorkspaceCreateParams) -> OcWorkspace:
        data = self._transport.request(
            "POST",
            f"/opencomputers/hosts/{host_id}/workspaces",
            json_body=params.model_dump(exclude_none=True),
        )
        return OcWorkspace.model_validate(data)

    def get(self, host_id: str, workspace_id: str) -> OcWorkspace:
        data = self._transport.request(
            "GET", f"/opencomputers/hosts/{host_id}/workspaces/{workspace_id}"
        )
        return OcWorkspace.model_validate(data)

    def update(
        self, host_id: str, workspace_id: str, params: OcWorkspaceUpdateParams
    ) -> OcWorkspace:
        data = self._transport.request(
            "PATCH",
            f"/opencomputers/hosts/{host_id}/workspaces/{workspace_id}",
            json_body=params.model_dump(exclude_none=True),
        )
        return OcWorkspace.model_validate(data)

    def delete(self, host_id: str, workspace_id: str) -> None:
        self._transport.request(
            "DELETE", f"/opencomputers/hosts/{host_id}/workspaces/{workspace_id}"
        )

    def pull(self, host_id: str, workspace_id: str) -> OcWorkspace:
        data = self._transport.request(
            "POST", f"/opencomputers/hosts/{host_id}/workspaces/{workspace_id}/pull"
        )
        return OcWorkspace.model_validate(data)

    def open_terminal(self, host_id: str, workspace_id: str) -> WsTicket:
        """Open a terminal scoped to the workspace root. Returns a WS ticket."""
        data = self._transport.request(
            "POST", f"/opencomputers/hosts/{host_id}/workspaces/{workspace_id}/open-terminal"
        )
        return WsTicket.model_validate(data)

    def events(self, host_id: str, workspace_id: str) -> Iterator[OcWorkspaceEvent]:
        for raw in self._transport.stream_sse(
            f"/opencomputers/hosts/{host_id}/workspaces/{workspace_id}/events"
        ):
            yield _parse_ws_event(raw)


class AsyncOcWorkspacesResource:
    """Git-backed workspace environments on a remote host (async)."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def list_all(self) -> OcWorkspaceListResponse:
        data = await self._transport.request("GET", "/opencomputers/workspaces")
        return OcWorkspaceListResponse.model_validate(data)

    async def list(self, host_id: str) -> OcWorkspaceListResponse:
        data = await self._transport.request(
            "GET", f"/opencomputers/hosts/{host_id}/workspaces"
        )
        return OcWorkspaceListResponse.model_validate(data)

    async def create(self, host_id: str, params: OcWorkspaceCreateParams) -> OcWorkspace:
        data = await self._transport.request(
            "POST",
            f"/opencomputers/hosts/{host_id}/workspaces",
            json_body=params.model_dump(exclude_none=True),
        )
        return OcWorkspace.model_validate(data)

    async def get(self, host_id: str, workspace_id: str) -> OcWorkspace:
        data = await self._transport.request(
            "GET", f"/opencomputers/hosts/{host_id}/workspaces/{workspace_id}"
        )
        return OcWorkspace.model_validate(data)

    async def update(
        self, host_id: str, workspace_id: str, params: OcWorkspaceUpdateParams
    ) -> OcWorkspace:
        data = await self._transport.request(
            "PATCH",
            f"/opencomputers/hosts/{host_id}/workspaces/{workspace_id}",
            json_body=params.model_dump(exclude_none=True),
        )
        return OcWorkspace.model_validate(data)

    async def delete(self, host_id: str, workspace_id: str) -> None:
        await self._transport.request(
            "DELETE", f"/opencomputers/hosts/{host_id}/workspaces/{workspace_id}"
        )

    async def pull(self, host_id: str, workspace_id: str) -> OcWorkspace:
        data = await self._transport.request(
            "POST", f"/opencomputers/hosts/{host_id}/workspaces/{workspace_id}/pull"
        )
        return OcWorkspace.model_validate(data)

    async def open_terminal(self, host_id: str, workspace_id: str) -> WsTicket:
        data = await self._transport.request(
            "POST",
            f"/opencomputers/hosts/{host_id}/workspaces/{workspace_id}/open-terminal",
        )
        return WsTicket.model_validate(data)

    async def events(self, host_id: str, workspace_id: str) -> AsyncIterator[OcWorkspaceEvent]:
        async for raw in self._transport.stream_sse(
            f"/opencomputers/hosts/{host_id}/workspaces/{workspace_id}/events"
        ):
            yield _parse_ws_event(raw)
