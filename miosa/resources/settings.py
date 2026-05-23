"""Tenant settings — main config + branding + provider keys."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(
    data: Any,
    keys: tuple[str, ...] = (
        "data",
        "settings",
        "branding",
        "provider_keys",
        "items",
    ),
) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class Settings:
    """Tenant settings — workspace config, branding, BYOK provider keys."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def get(self) -> Dict[str, Any]:
        """Get the current tenant settings."""
        return _unwrap(self._t.request("GET", "/settings"))

    def update(self, **attrs: Any) -> Dict[str, Any]:
        """Update tenant settings."""
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(self._t.request("PUT", "/settings", json_body=body))

    # ── Branding ────────────────────────────────────────────────────────

    def get_branding(self) -> Dict[str, Any]:
        """Get tenant branding (logo, colors, custom wordmark)."""
        return _unwrap(self._t.request("GET", "/settings/branding"))

    def update_branding(self, **attrs: Any) -> Dict[str, Any]:
        """Update tenant branding."""
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            self._t.request("PUT", "/settings/branding", json_body=body)
        )

    # ── Read-only reference data ────────────────────────────────────────

    def compute_pricing(self) -> Any:
        """Get tenant-scoped compute pricing."""
        return _unwrap(self._t.request("GET", "/settings/compute-pricing"))

    def gpu_pricing(self) -> Any:
        """Get tenant-scoped GPU pricing."""
        return _unwrap(self._t.request("GET", "/settings/gpu-pricing"))

    def available_models(self) -> Any:
        """List models available to this tenant."""
        return _unwrap(self._t.request("GET", "/settings/available-models"))

    def regions(self) -> Any:
        """List regions enabled for this tenant."""
        return _unwrap(self._t.request("GET", "/settings/regions"))

    # ── BYOK provider keys ──────────────────────────────────────────────

    def list_provider_keys(self) -> List[Dict[str, Any]]:
        """List tenant-level BYOK provider keys (Anthropic, OpenAI, etc.)."""
        data = self._t.request("GET", "/settings/provider-keys")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def upsert_provider_key(
        self, provider: str, *, key: str, **attrs: Any
    ) -> Dict[str, Any]:
        """Create or update a BYOK provider key."""
        body = {"key": key, **{k: v for k, v in attrs.items() if v is not None}}
        return _unwrap(
            self._t.request(
                "PUT", f"/settings/provider-keys/{provider}", json_body=body
            )
        )

    def delete_provider_key(self, provider: str) -> None:
        """Delete a BYOK provider key."""
        self._t.request("DELETE", f"/settings/provider-keys/{provider}")


class AsyncSettings:
    """Async tenant settings."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def get(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", "/settings"))

    async def update(self, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(await self._t.request("PUT", "/settings", json_body=body))

    async def get_branding(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", "/settings/branding"))

    async def update_branding(self, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            await self._t.request("PUT", "/settings/branding", json_body=body)
        )

    async def compute_pricing(self) -> Any:
        return _unwrap(await self._t.request("GET", "/settings/compute-pricing"))

    async def gpu_pricing(self) -> Any:
        return _unwrap(await self._t.request("GET", "/settings/gpu-pricing"))

    async def available_models(self) -> Any:
        return _unwrap(await self._t.request("GET", "/settings/available-models"))

    async def regions(self) -> Any:
        return _unwrap(await self._t.request("GET", "/settings/regions"))

    async def list_provider_keys(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", "/settings/provider-keys")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def upsert_provider_key(
        self, provider: str, *, key: str, **attrs: Any
    ) -> Dict[str, Any]:
        body = {"key": key, **{k: v for k, v in attrs.items() if v is not None}}
        return _unwrap(
            await self._t.request(
                "PUT", f"/settings/provider-keys/{provider}", json_body=body
            )
        )

    async def delete_provider_key(self, provider: str) -> None:
        await self._t.request("DELETE", f"/settings/provider-keys/{provider}")
