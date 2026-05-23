"""OpenComputers Secrets resource — sync and async variants."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List

from .types import Secret, SecretCreateParams, SecretUpdateParams

if TYPE_CHECKING:
    from ..._http import AsyncTransport, SyncTransport


class SecretsResource:
    """Encrypted per-host / per-tenant env var management (sync)."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    # -- Tenant-scoped --

    def list_for_tenant(self) -> List[Secret]:
        result = self._transport.request("GET", "/opencomputers/secrets")
        return [Secret.model_validate(s) for s in result.get("data", [])]

    def create_for_tenant(self, params: SecretCreateParams) -> Secret:
        data = self._transport.request(
            "POST", "/opencomputers/secrets", json_body=params.model_dump(exclude_none=True)
        )
        return Secret.model_validate(data)

    # -- Host-scoped --

    def list_for_host(self, host_id: str) -> List[Secret]:
        result = self._transport.request("GET", f"/opencomputers/hosts/{host_id}/secrets")
        return [Secret.model_validate(s) for s in result.get("data", [])]

    def create_for_host(self, host_id: str, params: SecretCreateParams) -> Secret:
        data = self._transport.request(
            "POST",
            f"/opencomputers/hosts/{host_id}/secrets",
            json_body=params.model_dump(exclude_none=True),
        )
        return Secret.model_validate(data)

    def update_for_host(
        self, host_id: str, secret_id: str, params: SecretUpdateParams
    ) -> Secret:
        data = self._transport.request(
            "PATCH",
            f"/opencomputers/hosts/{host_id}/secrets/{secret_id}",
            json_body=params.model_dump(exclude_none=True),
        )
        return Secret.model_validate(data)

    def delete_for_host(self, host_id: str, secret_id: str) -> None:
        self._transport.request(
            "DELETE", f"/opencomputers/hosts/{host_id}/secrets/{secret_id}"
        )

    def reveal(self, host_id: str, secret_id: str) -> Dict[str, str]:
        """Decrypt and return the plaintext value. Audit-logged."""
        return self._transport.request(
            "POST", f"/opencomputers/hosts/{host_id}/secrets/{secret_id}/reveal"
        )


class AsyncSecretsResource:
    """Encrypted per-host / per-tenant env var management (async)."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def list_for_tenant(self) -> List[Secret]:
        result = await self._transport.request("GET", "/opencomputers/secrets")
        return [Secret.model_validate(s) for s in result.get("data", [])]

    async def create_for_tenant(self, params: SecretCreateParams) -> Secret:
        data = await self._transport.request(
            "POST", "/opencomputers/secrets", json_body=params.model_dump(exclude_none=True)
        )
        return Secret.model_validate(data)

    async def list_for_host(self, host_id: str) -> List[Secret]:
        result = await self._transport.request(
            "GET", f"/opencomputers/hosts/{host_id}/secrets"
        )
        return [Secret.model_validate(s) for s in result.get("data", [])]

    async def create_for_host(self, host_id: str, params: SecretCreateParams) -> Secret:
        data = await self._transport.request(
            "POST",
            f"/opencomputers/hosts/{host_id}/secrets",
            json_body=params.model_dump(exclude_none=True),
        )
        return Secret.model_validate(data)

    async def update_for_host(
        self, host_id: str, secret_id: str, params: SecretUpdateParams
    ) -> Secret:
        data = await self._transport.request(
            "PATCH",
            f"/opencomputers/hosts/{host_id}/secrets/{secret_id}",
            json_body=params.model_dump(exclude_none=True),
        )
        return Secret.model_validate(data)

    async def delete_for_host(self, host_id: str, secret_id: str) -> None:
        await self._transport.request(
            "DELETE", f"/opencomputers/hosts/{host_id}/secrets/{secret_id}"
        )

    async def reveal(self, host_id: str, secret_id: str) -> Dict[str, str]:
        return await self._transport.request(
            "POST", f"/opencomputers/hosts/{host_id}/secrets/{secret_id}/reveal"
        )
