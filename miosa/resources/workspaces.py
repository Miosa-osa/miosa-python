"""Workspaces — top-level tenant workspaces grouping computers.

A workspace is a logical bucket of computers (handy for teams / projects).
Accessed via ``miosa.workspaces`` on the top-level client.

Example::

    ws = client.workspaces.create(name="prod")
    computers = client.workspaces.list_computers(ws.id)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..types import (
    Computer as ComputerModel,
)
from ..types import (
    WorkspaceCreate,
    WorkspaceData,
    WorkspaceUpdate,
)

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport
    from .computer import AsyncComputer, Computer


def _unwrap(data: Any, key: str = "data") -> Any:
    """Unwrap ``{"data": ...}`` envelopes if present."""
    if isinstance(data, dict) and key in data and len(data) <= 2:
        return data[key]
    return data


class Workspaces:
    """Synchronous workspace management."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def create(
        self,
        name: str,
        *,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkspaceData:
        """Create a new workspace.

        Example::

            ws = client.workspaces.create(name="prod", description="prod team")
        """
        body = WorkspaceCreate(
            name=name, slug=slug, description=description, metadata=metadata
        )
        data = self._transport.request(
            "POST", "/workspaces", json_body=body.model_dump(exclude_none=True)
        )
        return WorkspaceData.model_validate(_unwrap(data))

    def list(self) -> List[WorkspaceData]:
        """List all workspaces visible to the current credential."""
        data = self._transport.request("GET", "/workspaces")
        items = _unwrap(data, "data") if isinstance(data, dict) else data
        if isinstance(items, dict) and "workspaces" in items:
            items = items["workspaces"]
        return [WorkspaceData.model_validate(w) for w in (items or [])]

    def get(self, workspace_id: str) -> WorkspaceData:
        """Get a single workspace by ID."""
        data = self._transport.request("GET", f"/workspaces/{workspace_id}")
        return WorkspaceData.model_validate(_unwrap(data))

    def update(
        self,
        workspace_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkspaceData:
        """Update a workspace's metadata."""
        body = WorkspaceUpdate(name=name, description=description, metadata=metadata)
        data = self._transport.request(
            "PATCH",
            f"/workspaces/{workspace_id}",
            json_body=body.model_dump(exclude_none=True),
        )
        return WorkspaceData.model_validate(_unwrap(data))

    def delete(self, workspace_id: str) -> None:
        """Delete a workspace. Does not delete member computers."""
        self._transport.request("DELETE", f"/workspaces/{workspace_id}")

    def list_computers(self, workspace_id: str) -> List[Computer]:
        """List all computers that belong to the given workspace."""
        # Local import to avoid circular dep.
        from .computer import Computer

        data = self._transport.request(
            "GET", f"/workspaces/{workspace_id}/computers"
        )
        items: list = []
        if isinstance(data, dict):
            items = data.get("computers") or data.get("data") or []
        elif isinstance(data, list):
            items = data
        return [
            Computer(self._transport, ComputerModel.model_validate(item))
            for item in items
        ]

    def update_settings(
        self, workspace_id: str, settings: Dict[str, Any]
    ) -> WorkspaceData:
        """Update workspace-level settings."""
        data = self._transport.request(
            "PUT",
            f"/workspaces/{workspace_id}/settings",
            json_body=settings,
        )
        return WorkspaceData.model_validate(_unwrap(data))

    def list_sandboxes(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List all sandboxes that belong to this workspace."""
        data = self._transport.request(
            "GET", f"/workspaces/{workspace_id}/sandboxes"
        )
        items = _unwrap(data)
        if isinstance(items, dict):
            items = items.get("data", items.get("sandboxes", []))
        return items if isinstance(items, list) else []

    def list_deployments(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List all deployments that belong to this workspace."""
        data = self._transport.request(
            "GET", f"/workspaces/{workspace_id}/deployments"
        )
        items = _unwrap(data)
        if isinstance(items, dict):
            items = items.get("data", items.get("deployments", []))
        return items if isinstance(items, list) else []

    def list_databases(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List all managed databases that belong to this workspace."""
        data = self._transport.request(
            "GET", f"/workspaces/{workspace_id}/databases"
        )
        items = _unwrap(data)
        if isinstance(items, dict):
            items = items.get("data", items.get("databases", []))
        return items if isinstance(items, list) else []

    def list_projects(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List all projects that belong to this workspace."""
        data = self._transport.request(
            "GET", f"/workspaces/{workspace_id}/projects"
        )
        items = _unwrap(data)
        if isinstance(items, dict):
            items = items.get("data", items.get("projects", []))
        return items if isinstance(items, list) else []

    def get_stats(self, workspace_id: str) -> Dict[str, Any]:
        """Return aggregate resource stats for this workspace."""
        data = self._transport.request(
            "GET", f"/workspaces/{workspace_id}/stats"
        )
        return _unwrap(data) if isinstance(data, dict) else data

    def get_usage(self, workspace_id: str) -> Dict[str, Any]:
        """Return metered usage data for this workspace."""
        data = self._transport.request(
            "GET", f"/workspaces/{workspace_id}/usage"
        )
        return _unwrap(data) if isinstance(data, dict) else data


class AsyncWorkspaces:
    """Asynchronous workspace management."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def create(
        self,
        name: str,
        *,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkspaceData:
        body = WorkspaceCreate(
            name=name, slug=slug, description=description, metadata=metadata
        )
        data = await self._transport.request(
            "POST", "/workspaces", json_body=body.model_dump(exclude_none=True)
        )
        return WorkspaceData.model_validate(_unwrap(data))

    async def list(self) -> List[WorkspaceData]:
        data = await self._transport.request("GET", "/workspaces")
        items = _unwrap(data, "data") if isinstance(data, dict) else data
        if isinstance(items, dict) and "workspaces" in items:
            items = items["workspaces"]
        return [WorkspaceData.model_validate(w) for w in (items or [])]

    async def get(self, workspace_id: str) -> WorkspaceData:
        data = await self._transport.request("GET", f"/workspaces/{workspace_id}")
        return WorkspaceData.model_validate(_unwrap(data))

    async def update(
        self,
        workspace_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkspaceData:
        body = WorkspaceUpdate(name=name, description=description, metadata=metadata)
        data = await self._transport.request(
            "PATCH",
            f"/workspaces/{workspace_id}",
            json_body=body.model_dump(exclude_none=True),
        )
        return WorkspaceData.model_validate(_unwrap(data))

    async def delete(self, workspace_id: str) -> None:
        await self._transport.request("DELETE", f"/workspaces/{workspace_id}")

    async def list_computers(self, workspace_id: str) -> List[AsyncComputer]:
        from .computer import AsyncComputer

        data = await self._transport.request(
            "GET", f"/workspaces/{workspace_id}/computers"
        )
        items: list = []
        if isinstance(data, dict):
            items = data.get("computers") or data.get("data") or []
        elif isinstance(data, list):
            items = data
        return [
            AsyncComputer(self._transport, ComputerModel.model_validate(item))
            for item in items
        ]

    async def update_settings(
        self, workspace_id: str, settings: Dict[str, Any]
    ) -> WorkspaceData:
        """Update workspace-level settings."""
        data = await self._transport.request(
            "PUT",
            f"/workspaces/{workspace_id}/settings",
            json_body=settings,
        )
        return WorkspaceData.model_validate(_unwrap(data))

    async def list_sandboxes(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List all sandboxes that belong to this workspace."""
        data = await self._transport.request(
            "GET", f"/workspaces/{workspace_id}/sandboxes"
        )
        items = _unwrap(data)
        if isinstance(items, dict):
            items = items.get("data", items.get("sandboxes", []))
        return items if isinstance(items, list) else []

    async def list_deployments(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List all deployments that belong to this workspace."""
        data = await self._transport.request(
            "GET", f"/workspaces/{workspace_id}/deployments"
        )
        items = _unwrap(data)
        if isinstance(items, dict):
            items = items.get("data", items.get("deployments", []))
        return items if isinstance(items, list) else []

    async def list_databases(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List all managed databases that belong to this workspace."""
        data = await self._transport.request(
            "GET", f"/workspaces/{workspace_id}/databases"
        )
        items = _unwrap(data)
        if isinstance(items, dict):
            items = items.get("data", items.get("databases", []))
        return items if isinstance(items, list) else []

    async def list_projects(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List all projects that belong to this workspace."""
        data = await self._transport.request(
            "GET", f"/workspaces/{workspace_id}/projects"
        )
        items = _unwrap(data)
        if isinstance(items, dict):
            items = items.get("data", items.get("projects", []))
        return items if isinstance(items, list) else []

    async def get_stats(self, workspace_id: str) -> Dict[str, Any]:
        """Return aggregate resource stats for this workspace."""
        data = await self._transport.request(
            "GET", f"/workspaces/{workspace_id}/stats"
        )
        return _unwrap(data) if isinstance(data, dict) else data

    async def get_usage(self, workspace_id: str) -> Dict[str, Any]:
        """Return metered usage data for this workspace."""
        data = await self._transport.request(
            "GET", f"/workspaces/{workspace_id}/usage"
        )
        return _unwrap(data) if isinstance(data, dict) else data
