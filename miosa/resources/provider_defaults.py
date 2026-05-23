"""Provider defaults — admin LLM provider routing config.

Routes live under ``/api/v1/admin/provider-defaults`` and per-tenant
overrides under ``/api/v1/admin/tenants/:id/provider-config``. They
require an admin credential (``msk_a_*`` / ``msk_p_*`` or admin JWT).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(
    data: Any,
    keys: tuple[str, ...] = ("data", "defaults", "provider_defaults", "config"),
) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class ProviderDefaults:
    """Admin: read + write fleet-wide LLM provider defaults."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self) -> Dict[str, Any]:
        """Get the current provider defaults (GET ``/admin/provider-defaults``)."""
        return _unwrap(self._t.request("GET", "/admin/provider-defaults"))

    def get(self, provider: str) -> Dict[str, Any]:
        """Return the defaults entry for a single provider, or {} if missing."""
        data = self.list()
        if isinstance(data, dict):
            providers = data.get("providers") or data
            if isinstance(providers, dict) and provider in providers:
                return providers[provider]
        return {}

    def update(self, **opts: Any) -> Dict[str, Any]:
        """Replace the fleet-wide defaults (PUT ``/admin/provider-defaults``)."""
        body = {k: v for k, v in opts.items() if v is not None}
        return _unwrap(
            self._t.request("PUT", "/admin/provider-defaults", json_body=body)
        )

    # ── Per-tenant overrides ────────────────────────────────────────────

    def get_tenant(self, tenant_id: str) -> Dict[str, Any]:
        return _unwrap(
            self._t.request("GET", f"/admin/tenants/{tenant_id}/provider-config")
        )

    def set_tenant(self, tenant_id: str, **opts: Any) -> Dict[str, Any]:
        body = {k: v for k, v in opts.items() if v is not None}
        return _unwrap(
            self._t.request(
                "PUT",
                f"/admin/tenants/{tenant_id}/provider-config",
                json_body=body,
            )
        )

    def reset_tenant(self, tenant_id: str) -> None:
        self._t.request("DELETE", f"/admin/tenants/{tenant_id}/provider-config")


class AsyncProviderDefaults:
    """Async provider defaults."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", "/admin/provider-defaults"))

    async def get(self, provider: str) -> Dict[str, Any]:
        data = await self.list()
        if isinstance(data, dict):
            providers = data.get("providers") or data
            if isinstance(providers, dict) and provider in providers:
                return providers[provider]
        return {}

    async def update(self, **opts: Any) -> Dict[str, Any]:
        body = {k: v for k, v in opts.items() if v is not None}
        return _unwrap(
            await self._t.request(
                "PUT", "/admin/provider-defaults", json_body=body
            )
        )

    async def get_tenant(self, tenant_id: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "GET", f"/admin/tenants/{tenant_id}/provider-config"
            )
        )

    async def set_tenant(self, tenant_id: str, **opts: Any) -> Dict[str, Any]:
        body = {k: v for k, v in opts.items() if v is not None}
        return _unwrap(
            await self._t.request(
                "PUT",
                f"/admin/tenants/{tenant_id}/provider-config",
                json_body=body,
            )
        )

    async def reset_tenant(self, tenant_id: str) -> None:
        await self._t.request(
            "DELETE", f"/admin/tenants/{tenant_id}/provider-config"
        )
