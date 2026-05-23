"""Standalone tenant-scoped custom domains.

The per-computer / per-deployment domain APIs live on those resources;
this is the flat tenant-level list view (``/custom-domains``) for
white-label platforms managing many domains.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data", "domains", "items")) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class FlatCustomDomains:
    """Tenant-scoped custom domains (across all computers/deployments)."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request("GET", "/custom-domains", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def create(self, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(self._t.request("POST", "/custom-domains", json_body=body))

    def delete(self, domain_id: str) -> None:
        self._t.request("DELETE", f"/custom-domains/{domain_id}")


class AsyncFlatCustomDomains:
    """Async tenant-scoped custom domains."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request("GET", "/custom-domains", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def create(self, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(await self._t.request("POST", "/custom-domains", json_body=body))

    async def delete(self, domain_id: str) -> None:
        await self._t.request("DELETE", f"/custom-domains/{domain_id}")
