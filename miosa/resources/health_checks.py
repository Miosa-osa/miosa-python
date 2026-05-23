"""Health checks — uptime monitoring."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data", "health_checks", "items")) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class HealthChecks:
    """Health check / uptime monitor CRUD."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request("GET", "/health-checks", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def get(self, check_id: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("GET", f"/health-checks/{check_id}"))

    def create(self, *, name: str, url: str, **attrs: Any) -> Dict[str, Any]:
        body = {
            "name": name,
            "url": url,
            **{k: v for k, v in attrs.items() if v is not None},
        }
        return _unwrap(self._t.request("POST", "/health-checks", json_body=body))

    def update(self, check_id: str, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            self._t.request("PATCH", f"/health-checks/{check_id}", json_body=body)
        )

    def delete(self, check_id: str) -> None:
        self._t.request("DELETE", f"/health-checks/{check_id}")


class AsyncHealthChecks:
    """Async health checks."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request("GET", "/health-checks", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def get(self, check_id: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", f"/health-checks/{check_id}"))

    async def create(self, *, name: str, url: str, **attrs: Any) -> Dict[str, Any]:
        body = {
            "name": name,
            "url": url,
            **{k: v for k, v in attrs.items() if v is not None},
        }
        return _unwrap(await self._t.request("POST", "/health-checks", json_body=body))

    async def update(self, check_id: str, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            await self._t.request(
                "PATCH", f"/health-checks/{check_id}", json_body=body
            )
        )

    async def delete(self, check_id: str) -> None:
        await self._t.request("DELETE", f"/health-checks/{check_id}")
