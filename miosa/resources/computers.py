"""Computers resource — CRUD operations on the /computers collection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..types import Computer as ComputerModel
from ..types import ComputerCreate, ComputerSize, ComputerUpdate
from .computer import AsyncComputer, Computer

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _normalize_computer_size(size: str) -> ComputerSize:
    return ComputerSize("xl" if size == "xlarge" else size)


class ComputersResource:
    """Synchronous computers CRUD."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def create(
        self,
        name: str,
        *,
        template_type: str = "miosa-desktop",
        size: str = "small",
        metadata: dict[str, Any] | None = None,
        workspace_id: str | None = None,
        external_workspace_id: str | None = None,
        external_project_id: str | None = None,
        agent_runtime_profile_id: str | None = None,
        agent_profile_id: str | None = None,
        skip_agent_runtime_profile: bool | None = None,
    ) -> Computer:
        """Create a new computer and return a bound ``Computer`` object."""
        body = ComputerCreate(
            name=name,
            template_type=template_type,
            size=_normalize_computer_size(size),
            metadata=metadata,
            workspace_id=workspace_id,
            external_workspace_id=external_workspace_id,
            external_project_id=external_project_id,
            agent_runtime_profile_id=agent_runtime_profile_id,
            agent_profile_id=agent_profile_id,
            skip_agent_runtime_profile=skip_agent_runtime_profile,
        )
        data = self._transport.request(
            "POST", "/computers", json_body=body.model_dump(exclude_none=True)
        )
        model = ComputerModel.model_validate(data)
        return Computer(self._transport, model)

    def viewer_password(self, computer_id: str) -> dict[str, Any]:
        """Return whether the external/raw desktop viewer password is set.

        Authenticated MIOSA platform users should use the platform desktop
        entry URL and do not need this password. This is for raw external
        viewer links such as ``*.computer.miosa.ai/desktop/index.html``.
        """
        data = self._transport.request(
            "GET", f"/computers/{computer_id}/viewer-password"
        )
        if isinstance(data, dict) and "data" in data and len(data) <= 2:
            return data["data"]
        return data if isinstance(data, dict) else {}

    def rotate_viewer_password(self, computer_id: str) -> dict[str, Any]:
        """Rotate and return the external/raw desktop viewer password once."""
        data = self._transport.request(
            "POST", f"/computers/{computer_id}/viewer-password/rotate"
        )
        if isinstance(data, dict) and "data" in data and len(data) <= 2:
            return data["data"]
        return data if isinstance(data, dict) else {}

    def list(self, *, workspace_id: str | None = None) -> list[Computer]:
        """List all computers, optionally filtered to a workspace."""
        params: dict[str, Any] = {}
        if workspace_id is not None:
            params["workspace_id"] = workspace_id
        data = self._transport.request("GET", "/computers", params=params or None)
        items: list[dict] = []
        if isinstance(data, dict):
            # Platform API returns `{total, computers: [...]}`. Older shapes
            # returned `{data: [...]}` — both are accepted.
            items = data.get("computers") or data.get("data") or []
        elif isinstance(data, list):
            items = data
        return [
            Computer(self._transport, ComputerModel.model_validate(item))
            for item in items
        ]

    def get(self, computer_id: str) -> Computer:
        """Get a single computer by ID."""
        data = self._transport.request("GET", f"/computers/{computer_id}")
        model = ComputerModel.model_validate(data)
        return Computer(self._transport, model)

    def update(
        self,
        computer_id: str,
        *,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Computer:
        """Update a computer."""
        body = ComputerUpdate(name=name, metadata=metadata)
        data = self._transport.request(
            "PATCH",
            f"/computers/{computer_id}",
            json_body=body.model_dump(exclude_none=True),
        )
        model = ComputerModel.model_validate(data)
        return Computer(self._transport, model)

    def delete(self, computer_id: str) -> None:
        """Delete (destroy) a computer by ID."""
        self._transport.request("DELETE", f"/computers/{computer_id}")


class AsyncComputersResource:
    """Asynchronous computers CRUD."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def create(
        self,
        name: str,
        *,
        template_type: str = "miosa-desktop",
        size: str = "small",
        metadata: dict[str, Any] | None = None,
        workspace_id: str | None = None,
        external_workspace_id: str | None = None,
        external_project_id: str | None = None,
        agent_runtime_profile_id: str | None = None,
        agent_profile_id: str | None = None,
        skip_agent_runtime_profile: bool | None = None,
    ) -> AsyncComputer:
        body = ComputerCreate(
            name=name,
            template_type=template_type,
            size=_normalize_computer_size(size),
            metadata=metadata,
            workspace_id=workspace_id,
            external_workspace_id=external_workspace_id,
            external_project_id=external_project_id,
            agent_runtime_profile_id=agent_runtime_profile_id,
            agent_profile_id=agent_profile_id,
            skip_agent_runtime_profile=skip_agent_runtime_profile,
        )
        data = await self._transport.request(
            "POST", "/computers", json_body=body.model_dump(exclude_none=True)
        )
        model = ComputerModel.model_validate(data)
        return AsyncComputer(self._transport, model)

    async def viewer_password(self, computer_id: str) -> dict[str, Any]:
        data = await self._transport.request(
            "GET", f"/computers/{computer_id}/viewer-password"
        )
        if isinstance(data, dict) and "data" in data and len(data) <= 2:
            return data["data"]
        return data if isinstance(data, dict) else {}

    async def rotate_viewer_password(self, computer_id: str) -> dict[str, Any]:
        data = await self._transport.request(
            "POST", f"/computers/{computer_id}/viewer-password/rotate"
        )
        if isinstance(data, dict) and "data" in data and len(data) <= 2:
            return data["data"]
        return data if isinstance(data, dict) else {}

    async def list(self, *, workspace_id: str | None = None) -> list[AsyncComputer]:
        params: dict[str, Any] = {}
        if workspace_id is not None:
            params["workspace_id"] = workspace_id
        data = await self._transport.request("GET", "/computers", params=params or None)
        items: list[dict] = []
        if isinstance(data, dict):
            # Platform API returns `{total, computers: [...]}`. Older shapes
            # returned `{data: [...]}` — both are accepted.
            items = data.get("computers") or data.get("data") or []
        elif isinstance(data, list):
            items = data
        return [
            AsyncComputer(self._transport, ComputerModel.model_validate(item))
            for item in items
        ]

    async def get(self, computer_id: str) -> AsyncComputer:
        data = await self._transport.request("GET", f"/computers/{computer_id}")
        model = ComputerModel.model_validate(data)
        return AsyncComputer(self._transport, model)

    async def update(
        self,
        computer_id: str,
        *,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncComputer:
        body = ComputerUpdate(name=name, metadata=metadata)
        data = await self._transport.request(
            "PATCH",
            f"/computers/{computer_id}",
            json_body=body.model_dump(exclude_none=True),
        )
        model = ComputerModel.model_validate(data)
        return AsyncComputer(self._transport, model)

    async def delete(self, computer_id: str) -> None:
        await self._transport.request("DELETE", f"/computers/{computer_id}")
