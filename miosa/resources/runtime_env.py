"""Inherited runtime environment resources.

Runtime env vars define tenant/workspace/project defaults that are injected
into sandboxes, computers, deployments, and agent runtimes without returning
plaintext.
"""

from __future__ import annotations

from typing import Any

from .._http import AsyncTransport, SyncTransport


def _data(response: Any) -> Any:
    if isinstance(response, dict) and "data" in response:
        return response["data"]
    return response


def _payload(params: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "scope": params.get("scope"),
        "workspace_id": params.get("workspace_id") or params.get("workspaceId"),
        "project_id": params.get("project_id") or params.get("projectId"),
        "target": params.get("target"),
        "name": params.get("name"),
        "value": params.get("value"),
        "enabled": params.get("enabled"),
        "metadata": params.get("metadata"),
    }
    return {key: value for key, value in mapping.items() if value is not None}


class RuntimeEnv:
    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def list(
        self,
        *,
        scope: str | None = None,
        workspace_id: str | None = None,
        project_id: str | None = None,
        target: str | None = None,
    ) -> list[dict[str, Any]]:
        response = self._transport.request(
            "GET",
            "/runtime-env",
            params=_payload(
                {
                    "scope": scope,
                    "workspace_id": workspace_id,
                    "project_id": project_id,
                    "target": target,
                }
            ),
        )
        data = _data(response)
        return data if isinstance(data, list) else []

    def get(self, env_id: str) -> dict[str, Any]:
        return _data(self._transport.request("GET", f"/runtime-env/{env_id}"))

    def set(self, **params: Any) -> dict[str, Any]:
        return _data(
            self._transport.request("POST", "/runtime-env", json_body=_payload(params))
        )

    def delete(self, env_id: str) -> None:
        self._transport.request("DELETE", f"/runtime-env/{env_id}")


class AsyncRuntimeEnv:
    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def list(
        self,
        *,
        scope: str | None = None,
        workspace_id: str | None = None,
        project_id: str | None = None,
        target: str | None = None,
    ) -> list[dict[str, Any]]:
        response = await self._transport.request(
            "GET",
            "/runtime-env",
            params=_payload(
                {
                    "scope": scope,
                    "workspace_id": workspace_id,
                    "project_id": project_id,
                    "target": target,
                }
            ),
        )
        data = _data(response)
        return data if isinstance(data, list) else []

    async def get(self, env_id: str) -> dict[str, Any]:
        return _data(await self._transport.request("GET", f"/runtime-env/{env_id}"))

    async def set(self, **params: Any) -> dict[str, Any]:
        return _data(
            await self._transport.request(
                "POST", "/runtime-env", json_body=_payload(params)
            )
        )

    async def delete(self, env_id: str) -> None:
        await self._transport.request("DELETE", f"/runtime-env/{env_id}")
