"""OpenComputers Agents resource — sync and async variants."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING

from .types import (
    AgentDispatchParams,
    OcAgentEvent,
    OcAgentSession,
    OcAgentSessionListResponse,
)

if TYPE_CHECKING:
    from ..._http import AsyncTransport, SyncTransport


def _parse_agent_event(raw: dict) -> OcAgentEvent:
    data = raw.get("data", "")
    try:
        parsed = json.loads(data) if isinstance(data, str) and data else {}
    except (json.JSONDecodeError, ValueError):
        parsed = {"raw": data}
    return OcAgentEvent.model_validate(parsed)


def _session_payload(data: dict) -> dict:
    payload = data.get("session") or data.get("data") or data
    if "id" not in payload and payload.get("session_id"):
        payload = {**payload, "id": payload["session_id"]}
    return payload


def _list_payload(data: dict) -> dict:
    if "sessions" in data and "data" not in data:
        return {"data": data["sessions"], **data}
    if isinstance(data, list):
        return {"data": data}
    return data


class AgentsResource:
    """Dispatch and manage AI agent sessions on a remote host (sync)."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def _base(self, host_id: str) -> str:
        return f"/opencomputers/hosts/{host_id}/agent"

    def dispatch(self, host_id: str, params: AgentDispatchParams) -> OcAgentSession:
        """Dispatch a new agent session on the host."""
        data = self._transport.request(
            "POST",
            f"{self._base(host_id)}/dispatch",
            json_body=params.model_dump(exclude_none=True),
        )
        return OcAgentSession.model_validate(_session_payload(data))

    def list(self, host_id: str) -> OcAgentSessionListResponse:
        """List all agent sessions for a host."""
        data = self._transport.request("GET", f"{self._base(host_id)}/sessions")
        return OcAgentSessionListResponse.model_validate(_list_payload(data))

    def get(self, host_id: str, session_id: str) -> OcAgentSession:
        """Fetch a specific agent session."""
        data = self._transport.request("GET", f"{self._base(host_id)}/sessions/{session_id}")
        return OcAgentSession.model_validate(_session_payload(data))

    def events(self, host_id: str, session_id: str) -> Iterator[OcAgentEvent]:
        """Stream live events from an agent session."""
        for raw in self._transport.stream_sse(
            f"{self._base(host_id)}/sessions/{session_id}/events"
        ):
            yield _parse_agent_event(raw)

    def cancel(self, host_id: str, session_id: str) -> None:
        """Cancel a running or pending agent session."""
        self._transport.request("DELETE", f"{self._base(host_id)}/sessions/{session_id}")


class AsyncAgentsResource:
    """Dispatch and manage AI agent sessions on a remote host (async)."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    def _base(self, host_id: str) -> str:
        return f"/opencomputers/hosts/{host_id}/agent"

    async def dispatch(self, host_id: str, params: AgentDispatchParams) -> OcAgentSession:
        data = await self._transport.request(
            "POST",
            f"{self._base(host_id)}/dispatch",
            json_body=params.model_dump(exclude_none=True),
        )
        return OcAgentSession.model_validate(_session_payload(data))

    async def list(self, host_id: str) -> OcAgentSessionListResponse:
        data = await self._transport.request("GET", f"{self._base(host_id)}/sessions")
        return OcAgentSessionListResponse.model_validate(_list_payload(data))

    async def get(self, host_id: str, session_id: str) -> OcAgentSession:
        data = await self._transport.request(
            "GET", f"{self._base(host_id)}/sessions/{session_id}"
        )
        return OcAgentSession.model_validate(_session_payload(data))

    async def events(self, host_id: str, session_id: str) -> AsyncIterator[OcAgentEvent]:
        async for raw in self._transport.stream_sse(
            f"{self._base(host_id)}/sessions/{session_id}/events"
        ):
            yield _parse_agent_event(raw)

    async def cancel(self, host_id: str, session_id: str) -> None:
        await self._transport.request(
            "DELETE", f"{self._base(host_id)}/sessions/{session_id}"
        )
