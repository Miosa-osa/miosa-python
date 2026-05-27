"""Org Invites — email invite flow for org (tenant) membership.

Public endpoints (no auth):
    GET  /invites/:token

Authenticated endpoints (admin/owner role required for write ops):
    POST   /tenants/:id/invites
    GET    /tenants/:id/invites
    DELETE /tenants/:id/invites/:invite_id
    POST   /invites/:token/accept

Example::

    invite = client.org_invites.create(tenant_id, email="bob@example.com")
    print("invite URL:", invite["invite_url"])

    invites = client.org_invites.list(tenant_id)
    client.org_invites.revoke(tenant_id, invites[0]["id"])

    preview = client.org_invites.preview("some_token")
    if preview and not preview["expired"]:
        client.org_invites.accept("some_token")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport

OrgRole = Literal["owner", "admin", "member"]


def _data(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


class OrgInvites:
    """Synchronous org invite management."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def create(
        self,
        tenant_id: str,
        *,
        email: str,
        role: OrgRole = "member",
    ) -> Dict[str, Any]:
        """Create an org invite and dispatch the invite email.

        The response includes an ``invite_url`` that is host-aware: on
        white-label tenants it uses the custom domain.

        Requires ``admin`` or ``owner`` role in the tenant.

        ``POST /tenants/:id/invites``
        """
        data = self._transport.request(
            "POST",
            f"/tenants/{tenant_id}/invites",
            json_body={"email": email, "role": role},
        )
        return _data(data) if isinstance(data, dict) else data

    def list(self, tenant_id: str) -> List[Dict[str, Any]]:
        """List all pending org invites.

        Requires ``admin`` or ``owner`` role.

        ``GET /tenants/:id/invites``
        """
        data = self._transport.request(
            "GET", f"/tenants/{tenant_id}/invites"
        )
        return _data(data) if isinstance(data, dict) else (data or [])

    def revoke(self, tenant_id: str, invite_id: str) -> Dict[str, Any]:
        """Revoke a pending org invite.

        Returns 409 when the invite was already legitimately accepted.
        Requires ``admin`` or ``owner`` role.

        ``DELETE /tenants/:id/invites/:invite_id``
        """
        return self._transport.request(
            "DELETE", f"/tenants/{tenant_id}/invites/{invite_id}"
        )

    def preview(self, token: str) -> Optional[Dict[str, Any]]:
        """Preview an org invite by token (no auth required).

        Returns the preview dict or ``None`` when the token is unknown or has
        been revoked.

        ``GET /invites/:token``
        """
        try:
            data = self._transport.request("GET", f"/invites/{token}")
            return _data(data) if isinstance(data, dict) else data
        except Exception:
            return None

    def accept(self, token: str) -> Dict[str, Any]:
        """Accept an org invite on behalf of the authenticated user.

        The caller's JWT email must match the invite email (case-insensitive).

        Error responses:
          - 400 — invalid or expired token.
          - 422 ``EMAIL_MISMATCH`` — JWT email does not match invite email.

        ``POST /invites/:token/accept``
        """
        return self._transport.request(
            "POST", f"/invites/{token}/accept", json_body={}
        )


class AsyncOrgInvites:
    """Asynchronous org invite management."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def create(
        self,
        tenant_id: str,
        *,
        email: str,
        role: OrgRole = "member",
    ) -> Dict[str, Any]:
        """Create an org invite and dispatch the invite email.

        ``POST /tenants/:id/invites``
        """
        data = await self._transport.request(
            "POST",
            f"/tenants/{tenant_id}/invites",
            json_body={"email": email, "role": role},
        )
        return _data(data) if isinstance(data, dict) else data

    async def list(self, tenant_id: str) -> List[Dict[str, Any]]:
        """List all pending org invites.

        ``GET /tenants/:id/invites``
        """
        data = await self._transport.request(
            "GET", f"/tenants/{tenant_id}/invites"
        )
        return _data(data) if isinstance(data, dict) else (data or [])

    async def revoke(
        self, tenant_id: str, invite_id: str
    ) -> Dict[str, Any]:
        """Revoke a pending org invite.

        ``DELETE /tenants/:id/invites/:invite_id``
        """
        return await self._transport.request(
            "DELETE", f"/tenants/{tenant_id}/invites/{invite_id}"
        )

    async def preview(self, token: str) -> Optional[Dict[str, Any]]:
        """Preview an org invite by token (no auth required).

        ``GET /invites/:token``
        """
        try:
            data = await self._transport.request("GET", f"/invites/{token}")
            return _data(data) if isinstance(data, dict) else data
        except Exception:
            return None

    async def accept(self, token: str) -> Dict[str, Any]:
        """Accept an org invite on behalf of the authenticated user.

        ``POST /invites/:token/accept``
        """
        return await self._transport.request(
            "POST", f"/invites/{token}/accept", json_body={}
        )
