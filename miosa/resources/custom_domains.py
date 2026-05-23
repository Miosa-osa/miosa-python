"""Custom domain management for a Computer.

Accessed via ``computer.domains``. Map your own FQDNs to a computer and
let the platform handle CNAME verification + Caddy-issued TLS certs.

Example::

    domain = computer.domains.register("app.example.com")
    print(domain.instructions)
    # … add the CNAME record in your DNS registrar …
    verified = computer.domains.verify(domain.id)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List

from ..types import CustomDomainData

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, key: str = "data") -> Any:
    if isinstance(data, dict) and key in data and len(data) <= 2:
        return data[key]
    return data


class CustomDomains:
    """Synchronous custom-domain management."""

    def __init__(self, transport: SyncTransport, computer_id: str) -> None:
        self._transport = transport
        self._computer_id = computer_id

    def _base(self) -> str:
        return f"/computers/{self._computer_id}/domains"

    def register(self, fqdn: str) -> CustomDomainData:
        """Register a custom FQDN for this computer.

        Returns a record containing ``verification_target`` and ``instructions``
        — the CNAME the user must add to their DNS. Starts in ``pending``.
        """
        raw = self._transport.request(
            "POST", self._base(), json_body={"fqdn": fqdn}
        )
        return CustomDomainData.model_validate(_unwrap(raw))

    def list(self) -> List[CustomDomainData]:
        """List all custom domains registered for this computer."""
        raw = self._transport.request("GET", self._base())
        items = _unwrap(raw, "data") if isinstance(raw, dict) else raw
        return [CustomDomainData.model_validate(d) for d in (items or [])]

    def verify(self, domain_id: str) -> CustomDomainData:
        """Verify DNS ownership of a registered domain."""
        raw = self._transport.request(
            "POST", f"{self._base()}/{domain_id}/verify"
        )
        return CustomDomainData.model_validate(_unwrap(raw))

    def delete(self, domain_id: str) -> None:
        """Delete a custom domain mapping."""
        self._transport.request("DELETE", f"{self._base()}/{domain_id}")


class AsyncCustomDomains:
    """Asynchronous custom-domain management."""

    def __init__(self, transport: AsyncTransport, computer_id: str) -> None:
        self._transport = transport
        self._computer_id = computer_id

    def _base(self) -> str:
        return f"/computers/{self._computer_id}/domains"

    async def register(self, fqdn: str) -> CustomDomainData:
        raw = await self._transport.request(
            "POST", self._base(), json_body={"fqdn": fqdn}
        )
        return CustomDomainData.model_validate(_unwrap(raw))

    async def list(self) -> List[CustomDomainData]:
        raw = await self._transport.request("GET", self._base())
        items = _unwrap(raw, "data") if isinstance(raw, dict) else raw
        return [CustomDomainData.model_validate(d) for d in (items or [])]

    async def verify(self, domain_id: str) -> CustomDomainData:
        raw = await self._transport.request(
            "POST", f"{self._base()}/{domain_id}/verify"
        )
        return CustomDomainData.model_validate(_unwrap(raw))

    async def delete(self, domain_id: str) -> None:
        await self._transport.request(
            "DELETE", f"{self._base()}/{domain_id}"
        )
