"""Regions — datacenter availability, sizes, pricing, templates."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(
    data: Any,
    keys: tuple[str, ...] = (
        "data",
        "regions",
        "sizes",
        "pricing",
        "templates",
        "items",
    ),
) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class Regions:
    """Regions, sizes, pricing, and community templates (read-only catalog)."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list_regions(self) -> List[Dict[str, Any]]:
        """List datacenter regions."""
        data = self._t.request("GET", "/compute/regions")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def list_sizes(self) -> List[Dict[str, Any]]:
        """List available compute sizes."""
        data = self._t.request("GET", "/compute/sizes")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def pricing(self) -> Any:
        """Get static compute pricing data."""
        return _unwrap(self._t.request("GET", "/compute/pricing"))

    def list_templates(self) -> List[Dict[str, Any]]:
        """List community computer templates."""
        data = self._t.request("GET", "/compute/templates")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def get_template(self, template_id: str) -> Dict[str, Any]:
        """Get a single community template by id."""
        return _unwrap(self._t.request("GET", f"/compute/templates/{template_id}"))


class AsyncRegions:
    """Async regions."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list_regions(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", "/compute/regions")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def list_sizes(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", "/compute/sizes")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def pricing(self) -> Any:
        return _unwrap(await self._t.request("GET", "/compute/pricing"))

    async def list_templates(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", "/compute/templates")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def get_template(self, template_id: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request("GET", f"/compute/templates/{template_id}")
        )
