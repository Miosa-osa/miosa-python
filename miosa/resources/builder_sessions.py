"""Builder sessions — durable, cross-device Builder UI state.

Routes live under ``/api/v1/builder/sessions/`` and are part of the
public API surface (accepts ``msk_*`` API keys or JWT). Builder
sessions are ``optimal_sessions`` with ``resource_type = "sandbox"``
and ``vm_context.template_type = "miosa-sandbox"``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(
    data: Any, keys: tuple[str, ...] = ("data", "sessions", "items")
) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class BuilderSessions:
    """Builder UI session metadata (server-side, replaces localStorage)."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, *, limit: int = 50, **filters: Any) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit}
        params.update({k: v for k, v in filters.items() if v is not None})
        data = self._t.request("GET", "/builder/sessions", params=params)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def get(self, session_id: str) -> Dict[str, Any]:
        """Get a single session — falls back to filtering ``list()`` since the
        platform router only exposes index + title-update + delete."""
        for entry in self.list():
            if entry.get("id") == session_id:
                return entry
        return {}

    def update_title(self, session_id: str, title: str) -> Dict[str, Any]:
        body = {"title": title}
        return _unwrap(
            self._t.request(
                "PATCH",
                f"/builder/sessions/{session_id}/title",
                json_body=body,
            )
        )

    def delete(self, session_id: str) -> None:
        self._t.request("DELETE", f"/builder/sessions/{session_id}")


class AsyncBuilderSessions:
    """Async builder sessions."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(
        self, *, limit: int = 50, **filters: Any
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit}
        params.update({k: v for k, v in filters.items() if v is not None})
        data = await self._t.request("GET", "/builder/sessions", params=params)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def get(self, session_id: str) -> Dict[str, Any]:
        for entry in await self.list():
            if entry.get("id") == session_id:
                return entry
        return {}

    async def update_title(self, session_id: str, title: str) -> Dict[str, Any]:
        body = {"title": title}
        return _unwrap(
            await self._t.request(
                "PATCH",
                f"/builder/sessions/{session_id}/title",
                json_body=body,
            )
        )

    async def delete(self, session_id: str) -> None:
        await self._t.request("DELETE", f"/builder/sessions/{session_id}")
