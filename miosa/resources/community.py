"""Community — public template + agent catalog with install + rate.

Routes live under ``/api/v1/community/`` and require a JWT.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(
    data: Any,
    keys: tuple[str, ...] = ("data", "templates", "agents", "items"),
) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class Community:
    """Community template + agent catalog."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    # ── Agents ──────────────────────────────────────────────────────────

    def list_agents(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request("GET", "/community/agents", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("GET", f"/community/agents/{agent_id}"))

    # ── Templates ───────────────────────────────────────────────────────

    def list_templates(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request(
            "GET", "/community/templates", params=params or None
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def get_template(self, template_id: str) -> Dict[str, Any]:
        return _unwrap(
            self._t.request("GET", f"/community/templates/{template_id}")
        )

    def install_template(self, template_id: str, **opts: Any) -> Dict[str, Any]:
        """Install a community template into the caller's tenant."""
        body = {k: v for k, v in opts.items() if v is not None}
        return _unwrap(
            self._t.request(
                "POST",
                f"/community/templates/{template_id}/install",
                json_body=body,
            )
        )

    def rate_template(
        self, template_id: str, rating: int, **opts: Any
    ) -> Dict[str, Any]:
        """Rate a community template (1-5)."""
        body = {"rating": rating}
        body.update({k: v for k, v in opts.items() if v is not None})
        return _unwrap(
            self._t.request(
                "POST",
                f"/community/templates/{template_id}/rate",
                json_body=body,
            )
        )


class AsyncCommunity:
    """Async community catalog."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list_agents(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request(
            "GET", "/community/agents", params=params or None
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request("GET", f"/community/agents/{agent_id}")
        )

    async def list_templates(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request(
            "GET", "/community/templates", params=params or None
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def get_template(self, template_id: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request("GET", f"/community/templates/{template_id}")
        )

    async def install_template(
        self, template_id: str, **opts: Any
    ) -> Dict[str, Any]:
        body = {k: v for k, v in opts.items() if v is not None}
        return _unwrap(
            await self._t.request(
                "POST",
                f"/community/templates/{template_id}/install",
                json_body=body,
            )
        )

    async def rate_template(
        self, template_id: str, rating: int, **opts: Any
    ) -> Dict[str, Any]:
        body = {"rating": rating}
        body.update({k: v for k, v in opts.items() if v is not None})
        return _unwrap(
            await self._t.request(
                "POST",
                f"/community/templates/{template_id}/rate",
                json_body=body,
            )
        )
