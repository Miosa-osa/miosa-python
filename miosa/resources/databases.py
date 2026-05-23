"""Managed Postgres / databases resource."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, list_keys: tuple[str, ...] = ("data", "databases", "items")) -> Any:
    if isinstance(data, dict):
        for key in list_keys:
            if key in data:
                return data[key]
    return data


class Databases:
    """Managed database resource — list, create, lifecycle, credentials."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request("GET", "/databases", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def get(self, database_id: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("GET", f"/databases/{database_id}"))

    def create(self, **attrs: Any) -> Dict[str, Any]:
        idempotency_key = attrs.pop("idempotency_key", None) or attrs.pop(
            "idempotencyKey", None
        )
        if "engine_version" not in attrs and "version" in attrs:
            attrs["engine_version"] = attrs.pop("version")
        attrs.pop("size", None)

        body = {k: v for k, v in attrs.items() if v is not None}
        headers = (
            {"Idempotency-Key": str(idempotency_key)}
            if idempotency_key is not None
            else None
        )
        return _unwrap(
            self._t.request("POST", "/databases", json_body=body, headers=headers)
        )

    def delete(self, database_id: str) -> None:
        self._t.request("DELETE", f"/databases/{database_id}")

    # ── Lifecycle ──────────────────────────────────────────────────────

    def start(self, database_id: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("POST", f"/databases/{database_id}/start"))

    def stop(self, database_id: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("POST", f"/databases/{database_id}/stop"))

    def restart(self, database_id: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("POST", f"/databases/{database_id}/restart"))

    # ── Credentials + logs ────────────────────────────────────────────

    def credentials(self, database_id: str) -> Dict[str, Any]:
        """Get connection credentials (URL, host, port, user, password)."""
        return _unwrap(self._t.request("GET", f"/databases/{database_id}/credentials"))

    def logs(
        self,
        database_id: str,
        *,
        lines: Optional[int] = None,
        since: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get recent database logs."""
        params: Dict[str, Any] = {}
        if lines is not None:
            params["lines"] = lines
        if since is not None:
            params["since"] = since
        return self._t.request(
            "GET", f"/databases/{database_id}/logs", params=params or None
        )

    def stream_logs(self, database_id: str):
        """Stream database logs as Server-Sent Events."""
        return self._t.stream_sse(f"/databases/{database_id}/logs/stream")


class AsyncDatabases:
    """Async managed database resource."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request("GET", "/databases", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def get(self, database_id: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", f"/databases/{database_id}"))

    async def create(self, **attrs: Any) -> Dict[str, Any]:
        idempotency_key = attrs.pop("idempotency_key", None) or attrs.pop(
            "idempotencyKey", None
        )
        if "engine_version" not in attrs and "version" in attrs:
            attrs["engine_version"] = attrs.pop("version")
        attrs.pop("size", None)

        body = {k: v for k, v in attrs.items() if v is not None}
        headers = (
            {"Idempotency-Key": str(idempotency_key)}
            if idempotency_key is not None
            else None
        )
        return _unwrap(
            await self._t.request("POST", "/databases", json_body=body, headers=headers)
        )

    async def delete(self, database_id: str) -> None:
        await self._t.request("DELETE", f"/databases/{database_id}")

    async def start(self, database_id: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("POST", f"/databases/{database_id}/start"))

    async def stop(self, database_id: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("POST", f"/databases/{database_id}/stop"))

    async def restart(self, database_id: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("POST", f"/databases/{database_id}/restart"))

    async def credentials(self, database_id: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request("GET", f"/databases/{database_id}/credentials")
        )

    async def logs(
        self,
        database_id: str,
        *,
        lines: Optional[int] = None,
        since: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if lines is not None:
            params["lines"] = lines
        if since is not None:
            params["since"] = since
        return await self._t.request(
            "GET", f"/databases/{database_id}/logs", params=params or None
        )

    def stream_logs(self, database_id: str):
        return self._t.stream_sse(f"/databases/{database_id}/logs/stream")
