"""Organization discovery, switching, membership, and invites."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from urllib.parse import quote

from .org_invites import AsyncOrgInvites, OrgInvites, OrgRole

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


class OrganizationMembers:
    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def list(self, organization_id: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._transport.request("GET", f"/tenants/{quote(organization_id, safe='')}/members"),
        )

    def add(self, organization_id: str, user_id: str, role: OrgRole = "member") -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._transport.request(
                "POST",
                f"/tenants/{quote(organization_id, safe='')}/members",
                json_body={"user_id": user_id, "role": role},
            ),
        )

    def remove(self, organization_id: str, user_id: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._transport.request(
                "DELETE",
                f"/tenants/{quote(organization_id, safe='')}/members/{quote(user_id, safe='')}",
            ),
        )


class Organizations:
    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport
        self.members = OrganizationMembers(transport)
        self.invites = OrgInvites(transport)

    def list(self) -> list[dict[str, Any]]:
        response = self._transport.request("GET", "/platform/tenants")
        return (
            cast(list[dict[str, Any]], response.get("data", []))
            if isinstance(response, dict)
            else []
        )

    def current(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._transport.request("GET", "/platform/tenants/current"))

    def switch(self, id_or_slug: str) -> dict[str, Any]:
        """Switch a user JWT session. API keys cannot switch organizations."""
        return cast(
            dict[str, Any],
            self._transport.request(
                "POST", f"/platform/tenants/{quote(id_or_slug, safe='')}/switch", json_body={}
            ),
        )


class AsyncOrganizationMembers:
    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def list(self, organization_id: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._transport.request(
                "GET", f"/tenants/{quote(organization_id, safe='')}/members"
            ),
        )

    async def add(
        self, organization_id: str, user_id: str, role: OrgRole = "member"
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._transport.request(
                "POST",
                f"/tenants/{quote(organization_id, safe='')}/members",
                json_body={"user_id": user_id, "role": role},
            ),
        )

    async def remove(self, organization_id: str, user_id: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._transport.request(
                "DELETE",
                f"/tenants/{quote(organization_id, safe='')}/members/{quote(user_id, safe='')}",
            ),
        )


class AsyncOrganizations:
    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport
        self.members = AsyncOrganizationMembers(transport)
        self.invites = AsyncOrgInvites(transport)

    async def list(self) -> list[dict[str, Any]]:
        response = await self._transport.request("GET", "/platform/tenants")
        return (
            cast(list[dict[str, Any]], response.get("data", []))
            if isinstance(response, dict)
            else []
        )

    async def current(self) -> dict[str, Any]:
        return cast(
            dict[str, Any], await self._transport.request("GET", "/platform/tenants/current")
        )

    async def switch(self, id_or_slug: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._transport.request(
                "POST", f"/platform/tenants/{quote(id_or_slug, safe='')}/switch", json_body={}
            ),
        )
