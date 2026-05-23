"""Models — list available LLMs across providers.

Routes are exposed under ``/api/v1/intelligence/`` and require an
``mki_*`` intelligence key OR a JWT (dashboard users).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data", "models", "items")) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class Models:
    """List available LLM models routed through the MIOSA intelligence gateway."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        """List all models available to the calling tenant (OpenAI-compatible shape)."""
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request("GET", "/intelligence/models", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def get(self, model_id: str) -> Dict[str, Any]:
        """Get a single model by id.

        The platform router does not currently expose a per-model GET; this
        falls back to filtering the ``list()`` payload client-side.
        """
        for entry in self.list():
            if entry.get("id") == model_id:
                return entry
        return {}


class AsyncModels:
    """Async models surface."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request(
            "GET", "/intelligence/models", params=params or None
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def get(self, model_id: str) -> Dict[str, Any]:
        for entry in await self.list():
            if entry.get("id") == model_id:
                return entry
        return {}
