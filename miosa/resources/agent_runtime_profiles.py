"""Agent runtime profile resources.

Profiles define tenant/workspace defaults for agent runtimes, tools,
connectors, env, and policy mounted into sandboxes or computers.
"""

from __future__ import annotations

from typing import Any

from .._http import AsyncTransport, SyncTransport


def _data(response: Any) -> Any:
    if isinstance(response, dict) and "data" in response:
        return response["data"]
    return response


def _body(params: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "workspace_id": params.get("workspace_id") or params.get("workspaceId"),
        "project_id": params.get("project_id") or params.get("projectId"),
        "name": params.get("name"),
        "runtime": params.get("runtime"),
        "description": params.get("description"),
        "applies_to": params.get("applies_to") or params.get("appliesTo"),
        "tools": params.get("tools"),
        "connectors": params.get("connectors"),
        "env": params.get("env"),
        "policy": params.get("policy"),
        "metadata": params.get("metadata"),
        "is_default": params.get("is_default")
        if "is_default" in params
        else params.get("isDefault"),
    }
    return {key: value for key, value in mapping.items() if value is not None}


class AgentRuntimeProfiles:
    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def list(
        self, *, workspace_id: str | None = None, project_id: str | None = None
    ) -> list[dict[str, Any]]:
        response = self._transport.request(
            "GET",
            "/agent-runtime-profiles",
            params=_body({"workspace_id": workspace_id, "project_id": project_id}),
        )
        data = _data(response)
        return data if isinstance(data, list) else []

    def get(self, profile_id: str) -> dict[str, Any]:
        return _data(
            self._transport.request("GET", f"/agent-runtime-profiles/{profile_id}")
        )

    def create(self, **params: Any) -> dict[str, Any]:
        return _data(
            self._transport.request(
                "POST", "/agent-runtime-profiles", json_body=_body(params)
            )
        )

    def update(self, profile_id: str, **params: Any) -> dict[str, Any]:
        return _data(
            self._transport.request(
                "PUT",
                f"/agent-runtime-profiles/{profile_id}",
                json_body=_body(params),
            )
        )

    def delete(self, profile_id: str) -> None:
        self._transport.request("DELETE", f"/agent-runtime-profiles/{profile_id}")


class AsyncAgentRuntimeProfiles:
    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def list(
        self, *, workspace_id: str | None = None, project_id: str | None = None
    ) -> list[dict[str, Any]]:
        response = await self._transport.request(
            "GET",
            "/agent-runtime-profiles",
            params=_body({"workspace_id": workspace_id, "project_id": project_id}),
        )
        data = _data(response)
        return data if isinstance(data, list) else []

    async def get(self, profile_id: str) -> dict[str, Any]:
        return _data(
            await self._transport.request("GET", f"/agent-runtime-profiles/{profile_id}")
        )

    async def create(self, **params: Any) -> dict[str, Any]:
        return _data(
            await self._transport.request(
                "POST", "/agent-runtime-profiles", json_body=_body(params)
            )
        )

    async def update(self, profile_id: str, **params: Any) -> dict[str, Any]:
        return _data(
            await self._transport.request(
                "PUT",
                f"/agent-runtime-profiles/{profile_id}",
                json_body=_body(params),
            )
        )

    async def delete(self, profile_id: str) -> None:
        await self._transport.request("DELETE", f"/agent-runtime-profiles/{profile_id}")
