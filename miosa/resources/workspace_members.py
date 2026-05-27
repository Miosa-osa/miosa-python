"""Workspace Members — per-workspace user roster.

Endpoints covered::

    GET    /workspaces/:id/members
    POST   /workspaces/:id/members
    PATCH  /workspaces/:id/members/:user_id
    DELETE /workspaces/:id/members/:user_id

Example::

    members = client.workspace_members.list("ws_uuid")
    client.workspace_members.add("ws_uuid", user_id="usr_uuid", role="member")
    client.workspace_members.update_role("ws_uuid", "usr_uuid", role="admin")
    client.workspace_members.remove("ws_uuid", "usr_uuid")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport

WorkspaceRole = Literal["owner", "admin", "member", "viewer"]


def _data(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


class WorkspaceMembers:
    """Synchronous workspace member management."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def list(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List all members of a workspace.

        Returns denormalised rows including email, name, avatar_url, role, and
        joined_at for each member.

        ``GET /workspaces/:id/members``
        """
        data = self._transport.request(
            "GET", f"/workspaces/{workspace_id}/members"
        )
        return _data(data) if isinstance(data, dict) else (data or [])

    def add(
        self,
        workspace_id: str,
        *,
        user_id: str,
        role: WorkspaceRole = "member",
    ) -> Dict[str, Any]:
        """Add an existing tenant user to a workspace.

        The ``user_id`` must already hold a ``tenant_members`` row for the
        parent org. Use :meth:`workspace_invites.create` to invite someone who
        is not yet an org member.

        ``POST /workspaces/:id/members``

        :raises MiosaError: code ``NOT_TENANT_MEMBER`` if the user is not an
            org member.
        """
        body: Dict[str, Any] = {"user_id": user_id, "role": role}
        data = self._transport.request(
            "POST", f"/workspaces/{workspace_id}/members", json_body=body
        )
        return _data(data) if isinstance(data, dict) else data

    def update_role(
        self,
        workspace_id: str,
        user_id: str,
        *,
        role: WorkspaceRole,
    ) -> Dict[str, Any]:
        """Change a workspace member's role.

        ``PATCH /workspaces/:id/members/:user_id``
        """
        data = self._transport.request(
            "PATCH",
            f"/workspaces/{workspace_id}/members/{user_id}",
            json_body={"role": role},
        )
        return _data(data) if isinstance(data, dict) else data

    def remove(self, workspace_id: str, user_id: str) -> Dict[str, Any]:
        """Remove a user from a workspace.

        The last ``owner`` cannot be removed; promote another member first.

        ``DELETE /workspaces/:id/members/:user_id``

        :raises MiosaError: code ``LAST_OWNER`` if the target is the sole
            owner.
        """
        return self._transport.request(
            "DELETE", f"/workspaces/{workspace_id}/members/{user_id}"
        )


class AsyncWorkspaceMembers:
    """Asynchronous workspace member management."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def list(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List all members of a workspace.

        ``GET /workspaces/:id/members``
        """
        data = await self._transport.request(
            "GET", f"/workspaces/{workspace_id}/members"
        )
        return _data(data) if isinstance(data, dict) else (data or [])

    async def add(
        self,
        workspace_id: str,
        *,
        user_id: str,
        role: WorkspaceRole = "member",
    ) -> Dict[str, Any]:
        """Add an existing tenant user to a workspace.

        ``POST /workspaces/:id/members``
        """
        body: Dict[str, Any] = {"user_id": user_id, "role": role}
        data = await self._transport.request(
            "POST", f"/workspaces/{workspace_id}/members", json_body=body
        )
        return _data(data) if isinstance(data, dict) else data

    async def update_role(
        self,
        workspace_id: str,
        user_id: str,
        *,
        role: WorkspaceRole,
    ) -> Dict[str, Any]:
        """Change a workspace member's role.

        ``PATCH /workspaces/:id/members/:user_id``
        """
        data = await self._transport.request(
            "PATCH",
            f"/workspaces/{workspace_id}/members/{user_id}",
            json_body={"role": role},
        )
        return _data(data) if isinstance(data, dict) else data

    async def remove(self, workspace_id: str, user_id: str) -> Dict[str, Any]:
        """Remove a user from a workspace.

        ``DELETE /workspaces/:id/members/:user_id``
        """
        return await self._transport.request(
            "DELETE", f"/workspaces/{workspace_id}/members/{user_id}"
        )
