"""Tenant — current tenant info, preview domain, and branding."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data", "tenant", "branding", "items")) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class PreviewDomain:
    """Tenant preview-domain sub-resource."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def get(self) -> Dict[str, Any]:
        """GET /api/v1/tenant/preview-domain → {domain, verified_at, cname_target}"""
        return _unwrap(self._t.request("GET", "/tenant/preview-domain"))

    def set(self, domain: str) -> Dict[str, Any]:
        """PUT /api/v1/tenant/preview-domain → updated preview domain record."""
        return _unwrap(
            self._t.request(
                "PUT",
                "/tenant/preview-domain",
                json_body={"preview_domain": domain},
            )
        )

    def verify(self) -> Dict[str, Any]:
        """POST /api/v1/tenant/preview-domain/verify → {verified, target, records}"""
        return _unwrap(self._t.request("POST", "/tenant/preview-domain/verify", json_body={}))

    def delete(self) -> None:
        """DELETE /api/v1/tenant/preview-domain"""
        self._t.request("DELETE", "/tenant/preview-domain")


class AsyncPreviewDomain:
    """Async tenant preview-domain sub-resource."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def get(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", "/tenant/preview-domain"))

    async def set(self, domain: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "PUT",
                "/tenant/preview-domain",
                json_body={"preview_domain": domain},
            )
        )

    async def verify(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("POST", "/tenant/preview-domain/verify", json_body={}))

    async def delete(self) -> None:
        await self._t.request("DELETE", "/tenant/preview-domain")


class Branding:
    """Tenant branding sub-resource."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def get(self) -> Dict[str, Any]:
        """GET /api/v1/tenant/branding"""
        return _unwrap(self._t.request("GET", "/tenant/branding"))

    def set(self, branding: Dict[str, Any]) -> Dict[str, Any]:
        """PUT /api/v1/tenant/branding — keys: product_name, logo_url, support_url, support_email, primary_color, background_color"""
        return _unwrap(
            self._t.request(
                "PUT",
                "/tenant/branding",
                json_body={"branding": branding},
            )
        )

    def delete(self) -> None:
        """DELETE /api/v1/tenant/branding"""
        self._t.request("DELETE", "/tenant/branding")


class AsyncBranding:
    """Async tenant branding sub-resource."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def get(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", "/tenant/branding"))

    async def set(self, branding: Dict[str, Any]) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "PUT",
                "/tenant/branding",
                json_body={"branding": branding},
            )
        )

    async def delete(self) -> None:
        await self._t.request("DELETE", "/tenant/branding")


class Tenant:
    """Tenant info — read the current tenant's plan, manage preview domain and branding."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport
        self.preview_domain = PreviewDomain(transport)
        self.branding = Branding(transport)

    def current(self) -> Dict[str, Any]:
        """Get the current tenant's plan, limits, and live usage counters."""
        return _unwrap(self._t.request("GET", "/tenant/plan"))


class AsyncTenant:
    """Async tenant info."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport
        self.preview_domain = AsyncPreviewDomain(transport)
        self.branding = AsyncBranding(transport)

    async def current(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", "/tenant/plan"))
