"""Workspace Invites — email invite flow for workspace access.

Sending an invite to an email that already belongs to a tenant member
short-circuits to directly adding that user (returns ``type: "added"``).
Accepting a workspace invite for an unknown email auto-creates both a
``tenant_members`` and a ``workspace_members`` row atomically.

Endpoints covered::

    POST   /workspaces/:id/invites          (create — auth required)
    GET    /workspaces/:id/invites          (list  — auth required)
    DELETE /workspaces/:id/invites/:id      (revoke — auth required)
    GET    /workspace-invites/:token        (preview — public, no auth)
    POST   /workspace-invites/:token/accept (accept — auth required)

Example::

    result = client.workspace_invites.create("ws_uuid", email="alice@example.com")
    if result["type"] == "invited":
        print("invite sent to", result["data"]["email"])
    else:
        print("added directly as", result["data"]["role"])

    invites = client.workspace_invites.list("ws_uuid")
    client.workspace_invites.revoke("ws_uuid", invites[0]["id"])

    preview = client.workspace_invites.preview("some_token")
    if preview and not preview["expired"]:
        client.workspace_invites.accept("some_token")
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


class WorkspaceInvites:
    """Synchronous workspace invite management."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def create(
        self,
        workspace_id: str,
        *,
        email: str,
        role: WorkspaceRole = "member",
    ) -> Dict[str, Any]:
        """Create a workspace invite or add a member directly.

        If ``email`` already maps to a tenant member the user is added directly
        and ``type == "added"`` is returned with a WorkspaceMemberRecord.
        Otherwise an invite row is created and ``type == "invited"`` is
        returned.

        ``POST /workspaces/:id/invites``
        """
        return self._transport.request(
            "POST",
            f"/workspaces/{workspace_id}/invites",
            json_body={"email": email, "role": role},
        )

    def list(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List all pending workspace invites.

        ``GET /workspaces/:id/invites``
        """
        data = self._transport.request(
            "GET", f"/workspaces/{workspace_id}/invites"
        )
        return _data(data) if isinstance(data, dict) else (data or [])

    def revoke(self, workspace_id: str, invite_id: str) -> Dict[str, Any]:
        """Revoke a pending workspace invite.

        Already-revoked invites are idempotent. An invite that was legitimately
        accepted raises a 409 error.

        ``DELETE /workspaces/:id/invites/:invite_id``
        """
        return self._transport.request(
            "DELETE", f"/workspaces/{workspace_id}/invites/{invite_id}"
        )

    def preview(self, token: str) -> Optional[Dict[str, Any]]:
        """Preview a workspace invite by token (no auth required).

        Returns the preview dict or ``None`` when the token is unknown or
        has been revoked.

        ``GET /workspace-invites/:token``
        """
        try:
            data = self._transport.request(
                "GET", f"/workspace-invites/{token}"
            )
            return _data(data) if isinstance(data, dict) else data
        except Exception:
            return None

    def accept(self, token: str) -> Dict[str, Any]:
        """Accept a workspace invite on behalf of the authenticated user.

        The caller's JWT email must match the invite email (case-insensitive).

        Error codes:
          - ``INVALID_TOKEN`` (404) — token not found.
          - ``EXPIRED`` (410) — invite TTL elapsed.
          - ``REVOKED`` (409) — invite was revoked.
          - ``ALREADY_ACCEPTED`` (409) — already used.
          - ``EMAIL_MISMATCH`` (422) — JWT email differs from invite email.

        ``POST /workspace-invites/:token/accept``
        """
        return self._transport.request(
            "POST", f"/workspace-invites/{token}/accept", json_body={}
        )


class AsyncWorkspaceInvites:
    """Asynchronous workspace invite management."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def create(
        self,
        workspace_id: str,
        *,
        email: str,
        role: WorkspaceRole = "member",
    ) -> Dict[str, Any]:
        """Create a workspace invite or add a member directly.

        ``POST /workspaces/:id/invites``
        """
        return await self._transport.request(
            "POST",
            f"/workspaces/{workspace_id}/invites",
            json_body={"email": email, "role": role},
        )

    async def list(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List all pending workspace invites.

        ``GET /workspaces/:id/invites``
        """
        data = await self._transport.request(
            "GET", f"/workspaces/{workspace_id}/invites"
        )
        return _data(data) if isinstance(data, dict) else (data or [])

    async def revoke(
        self, workspace_id: str, invite_id: str
    ) -> Dict[str, Any]:
        """Revoke a pending workspace invite.

        ``DELETE /workspaces/:id/invites/:invite_id``
        """
        return await self._transport.request(
            "DELETE", f"/workspaces/{workspace_id}/invites/{invite_id}"
        )

    async def preview(self, token: str) -> Optional[Dict[str, Any]]:
        """Preview a workspace invite by token (no auth required).

        ``GET /workspace-invites/:token``
        """
        try:
            data = await self._transport.request(
                "GET", f"/workspace-invites/{token}"
            )
            return _data(data) if isinstance(data, dict) else data
        except Exception:
            return None

    async def accept(self, token: str) -> Dict[str, Any]:
        """Accept a workspace invite on behalf of the authenticated user.

        ``POST /workspace-invites/:token/accept``
        """
        return await self._transport.request(
            "POST", f"/workspace-invites/{token}/accept", json_body={}
        )
