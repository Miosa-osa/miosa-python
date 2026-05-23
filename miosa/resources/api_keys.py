"""API key management — programmatic key CRUD."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data", "keys", "api_keys", "items")) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class ApiKeys:
    """API key management. The plaintext key is returned ONLY at create time."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request("GET", "/api-keys", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def create(
        self,
        *,
        name: str,
        scopes: Optional[List[str]] = None,
        **attrs: Any,
    ) -> Dict[str, Any]:
        """Create an API key.

        The response contains a one-time plaintext ``token`` (or ``key``).
        Store it immediately; the server only keeps a hash.
        """
        body = {"name": name, **{k: v for k, v in attrs.items() if v is not None}}
        if scopes is not None:
            body["scopes"] = scopes
        return _unwrap(self._t.request("POST", "/api-keys", json_body=body))

    def delete(self, key_id: str) -> None:
        self._t.request("DELETE", f"/api-keys/{key_id}")


class AsyncApiKeys:
    """Async API key management."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request("GET", "/api-keys", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def create(
        self,
        *,
        name: str,
        scopes: Optional[List[str]] = None,
        **attrs: Any,
    ) -> Dict[str, Any]:
        body = {"name": name, **{k: v for k, v in attrs.items() if v is not None}}
        if scopes is not None:
            body["scopes"] = scopes
        return _unwrap(await self._t.request("POST", "/api-keys", json_body=body))

    async def delete(self, key_id: str) -> None:
        await self._t.request("DELETE", f"/api-keys/{key_id}")
