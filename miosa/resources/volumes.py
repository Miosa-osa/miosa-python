"""Persistent block storage volumes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data", "volumes", "items")) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class Volumes:
    """Persistent block storage volumes that survive instance restarts."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request("GET", "/volumes", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def get(self, volume_id: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("GET", f"/volumes/{volume_id}"))

    def create(
        self,
        *,
        name: str,
        size_gb: int,
        **attrs: Any,
    ) -> Dict[str, Any]:
        body = {
            "name": name,
            "size_gb": size_gb,
            **{k: v for k, v in attrs.items() if v is not None},
        }
        return _unwrap(self._t.request("POST", "/volumes", json_body=body))

    def delete(self, volume_id: str) -> None:
        self._t.request("DELETE", f"/volumes/{volume_id}")


class AsyncVolumes:
    """Async persistent volumes."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request("GET", "/volumes", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def get(self, volume_id: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", f"/volumes/{volume_id}"))

    async def create(
        self,
        *,
        name: str,
        size_gb: int,
        **attrs: Any,
    ) -> Dict[str, Any]:
        body = {
            "name": name,
            "size_gb": size_gb,
            **{k: v for k, v in attrs.items() if v is not None},
        }
        return _unwrap(await self._t.request("POST", "/volumes", json_body=body))

    async def delete(self, volume_id: str) -> None:
        await self._t.request("DELETE", f"/volumes/{volume_id}")
