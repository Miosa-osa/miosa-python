"""Computers resource — CRUD operations on the /computers collection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..types import Computer as ComputerModel, ComputerCreate, ComputerSize, ComputerUpdate
from .computer import AsyncComputer, Computer

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


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
        metadata: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None,
        external_workspace_id: Optional[str] = None,
        external_project_id: Optional[str] = None,
    ) -> Computer:
        """Create a new computer and return a bound ``Computer`` object."""
        body = ComputerCreate(
            name=name,
            template_type=template_type,
            size=ComputerSize(size),
            metadata=metadata,
            workspace_id=workspace_id,
            external_workspace_id=external_workspace_id,
            external_project_id=external_project_id,
        )
        data = self._transport.request(
            "POST", "/computers", json_body=body.model_dump(exclude_none=True)
        )
        model = ComputerModel.model_validate(data)
        return Computer(self._transport, model)

    def list(self, *, workspace_id: Optional[str] = None) -> List[Computer]:
        """List all computers, optionally filtered to a workspace."""
        params: Dict[str, Any] = {}
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
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
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
        metadata: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None,
        external_workspace_id: Optional[str] = None,
        external_project_id: Optional[str] = None,
    ) -> AsyncComputer:
        body = ComputerCreate(
            name=name,
            template_type=template_type,
            size=ComputerSize(size),
            metadata=metadata,
            workspace_id=workspace_id,
            external_workspace_id=external_workspace_id,
            external_project_id=external_project_id,
        )
        data = await self._transport.request(
            "POST", "/computers", json_body=body.model_dump(exclude_none=True)
        )
        model = ComputerModel.model_validate(data)
        return AsyncComputer(self._transport, model)

    async def list(self, *, workspace_id: Optional[str] = None) -> List[AsyncComputer]:
        params: Dict[str, Any] = {}
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
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
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
