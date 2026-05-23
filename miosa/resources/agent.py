"""Agent resource — CUA (Computer Use Agent) session management."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from ..types import AgentSession, AgentSessionCreate, AgentSessionList

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


class AgentResource:
    """Synchronous CUA session resource scoped to a single computer."""

    def __init__(self, transport: SyncTransport, computer_id: str) -> None:
        self._transport = transport
        self._computer_id = computer_id

    def _base(self) -> str:
        return f"/computers/{self._computer_id}/cua/sessions"

    def run(
        self,
        goal: str,
        *,
        model_id: Optional[str] = None,
        max_turns: Optional[int] = None,
    ) -> AgentSession:
        """Start a new CUA agent session."""
        body = AgentSessionCreate(goal=goal, model_id=model_id, max_turns=max_turns)
        data = self._transport.request(
            "POST", self._base(), json_body=body.model_dump(exclude_none=True)
        )
        return AgentSession.model_validate(data)

    def list(self) -> List[AgentSession]:
        """List all agent sessions for this computer."""
        data = self._transport.request("GET", self._base())
        if isinstance(data, dict):
            items = data.get("data") or data.get("sessions") or []
        elif isinstance(data, list):
            items = data
        else:
            items = []
        return [AgentSession.model_validate(item) for item in items]

    def get(self, session_id: str) -> AgentSession:
        """Get a single agent session by ID."""
        data = self._transport.request("GET", f"{self._base()}/{session_id}")
        return AgentSession.model_validate(data)

    def cancel(self, session_id: str) -> AgentSession:
        """Cancel (delete) an agent session."""
        data = self._transport.request("DELETE", f"{self._base()}/{session_id}")
        return AgentSession.model_validate(data)

    def task(self, session_id: str, instruction: str) -> AgentSession:
        """Send a mid-session instruction to a running CUA session."""
        data = self._transport.request(
            "POST",
            f"{self._base()}/{session_id}/task",
            json_body={"instruction": instruction},
        )
        return AgentSession.model_validate(data)

    def pause(self, session_id: str) -> AgentSession:
        """Pause a running CUA session."""
        data = self._transport.request(
            "POST", f"{self._base()}/{session_id}/pause", json_body={}
        )
        return AgentSession.model_validate(data)

    def resume(self, session_id: str) -> AgentSession:
        """Resume a paused CUA session."""
        data = self._transport.request(
            "POST", f"{self._base()}/{session_id}/resume", json_body={}
        )
        return AgentSession.model_validate(data)


class AsyncAgentResource:
    """Asynchronous CUA session resource scoped to a single computer."""

    def __init__(self, transport: AsyncTransport, computer_id: str) -> None:
        self._transport = transport
        self._computer_id = computer_id

    def _base(self) -> str:
        return f"/computers/{self._computer_id}/cua/sessions"

    async def run(
        self,
        goal: str,
        *,
        model_id: Optional[str] = None,
        max_turns: Optional[int] = None,
    ) -> AgentSession:
        body = AgentSessionCreate(goal=goal, model_id=model_id, max_turns=max_turns)
        data = await self._transport.request(
            "POST", self._base(), json_body=body.model_dump(exclude_none=True)
        )
        return AgentSession.model_validate(data)

    async def list(self) -> List[AgentSession]:
        data = await self._transport.request("GET", self._base())
        if isinstance(data, dict):
            items = data.get("data") or data.get("sessions") or []
        elif isinstance(data, list):
            items = data
        else:
            items = []
        return [AgentSession.model_validate(item) for item in items]

    async def get(self, session_id: str) -> AgentSession:
        data = await self._transport.request("GET", f"{self._base()}/{session_id}")
        return AgentSession.model_validate(data)

    async def cancel(self, session_id: str) -> AgentSession:
        data = await self._transport.request("DELETE", f"{self._base()}/{session_id}")
        return AgentSession.model_validate(data)

    async def task(self, session_id: str, instruction: str) -> AgentSession:
        """Send a mid-session instruction to a running CUA session."""
        data = await self._transport.request(
            "POST",
            f"{self._base()}/{session_id}/task",
            json_body={"instruction": instruction},
        )
        return AgentSession.model_validate(data)

    async def pause(self, session_id: str) -> AgentSession:
        """Pause a running CUA session."""
        data = await self._transport.request(
            "POST", f"{self._base()}/{session_id}/pause", json_body={}
        )
        return AgentSession.model_validate(data)

    async def resume(self, session_id: str) -> AgentSession:
        """Resume a paused CUA session."""
        data = await self._transport.request(
            "POST", f"{self._base()}/{session_id}/resume", json_body={}
        )
        return AgentSession.model_validate(data)
