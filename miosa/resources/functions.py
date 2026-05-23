"""Edge functions — serverless request-driven code."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data", "functions", "items")) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class Functions:
    """Edge functions — CRUD + invoke."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request("GET", "/functions", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def get(self, function_id: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("GET", f"/functions/{function_id}"))

    def create(self, *, name: str, **attrs: Any) -> Dict[str, Any]:
        body = {"name": name, **{k: v for k, v in attrs.items() if v is not None}}
        return _unwrap(self._t.request("POST", "/functions", json_body=body))

    def update(self, function_id: str, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            self._t.request("PATCH", f"/functions/{function_id}", json_body=body)
        )

    def delete(self, function_id: str) -> None:
        self._t.request("DELETE", f"/functions/{function_id}")

    def invoke(
        self,
        function_id: str,
        *,
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Invoke a function synchronously."""
        return self._t.request(
            "POST",
            f"/functions/{function_id}/invoke",
            json_body=payload or {},
            headers=headers,
        )


class AsyncFunctions:
    """Async edge functions."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request("GET", "/functions", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def get(self, function_id: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", f"/functions/{function_id}"))

    async def create(self, *, name: str, **attrs: Any) -> Dict[str, Any]:
        body = {"name": name, **{k: v for k, v in attrs.items() if v is not None}}
        return _unwrap(await self._t.request("POST", "/functions", json_body=body))

    async def update(self, function_id: str, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            await self._t.request("PATCH", f"/functions/{function_id}", json_body=body)
        )

    async def delete(self, function_id: str) -> None:
        await self._t.request("DELETE", f"/functions/{function_id}")

    async def invoke(
        self,
        function_id: str,
        *,
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        return await self._t.request(
            "POST",
            f"/functions/{function_id}/invoke",
            json_body=payload or {},
            headers=headers,
        )
