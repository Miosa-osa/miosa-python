"""App Engine appliance host resource.

App Engine is the MIOSA-managed workspace appliance model: one always-on
workspace host runs the white-labeled deployment appliance, and many app
containers can be served from that host once the appliance is healthy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..types import DockerDeployHost, DockerDeployTemplate

if TYPE_CHECKING:  # pragma: no cover
    from .._http import AsyncTransport, SyncTransport


def _unwrap_hosts(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, dict):
        rows = data.get("data") or data.get("hosts") or []
        return rows if isinstance(rows, list) else []
    return data if isinstance(data, list) else []


def _unwrap_host(data: Any) -> Dict[str, Any]:
    if isinstance(data, dict):
        host = data.get("data") or data.get("host")
        if isinstance(host, dict):
            return host
    raise ValueError("App Engine host response was empty.")


def _unwrap_templates(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, dict):
        rows = data.get("data") or data.get("templates") or []
        return rows if isinstance(rows, list) else []
    return data if isinstance(data, list) else []


def _unwrap_template(data: Any) -> Dict[str, Any]:
    if isinstance(data, dict):
        template = data.get("data") or data.get("template")
        if isinstance(template, dict):
            return template
    raise ValueError("App Engine template response was empty.")


def _ensure_body(
    *,
    workspace_id: Optional[str],
    external_workspace_id: Optional[str],
) -> Dict[str, str]:
    body: Dict[str, str] = {}
    if workspace_id:
        body["workspace_id"] = workspace_id
    if external_workspace_id:
        body["external_workspace_id"] = external_workspace_id
    return body


class DockerDeploy:
    """Synchronous App Engine host API."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._transport = transport

    def list_hosts(self, *, workspace_id: Optional[str] = None) -> List[DockerDeployHost]:
        params = {"workspace_id": workspace_id} if workspace_id else None
        data = self._transport.request("GET", "/docker-deploy/hosts", params=params)
        return [DockerDeployHost.model_validate(row) for row in _unwrap_hosts(data)]

    def ensure_host(
        self,
        *,
        workspace_id: Optional[str] = None,
        external_workspace_id: Optional[str] = None,
    ) -> DockerDeployHost:
        data = self._transport.request(
            "POST",
            "/docker-deploy/hosts/ensure",
            json_body=_ensure_body(
                workspace_id=workspace_id,
                external_workspace_id=external_workspace_id,
            ),
        )
        return DockerDeployHost.model_validate(_unwrap_host(data))

    def get_host(self, host_id: str) -> DockerDeployHost:
        data = self._transport.request("GET", f"/docker-deploy/hosts/{host_id}")
        return DockerDeployHost.model_validate(_unwrap_host(data))

    def list_templates(self) -> List[DockerDeployTemplate]:
        data = self._transport.request("GET", "/docker-deploy/templates")
        return [DockerDeployTemplate.model_validate(row) for row in _unwrap_templates(data)]

    def get_template(self, template_id: str) -> DockerDeployTemplate:
        data = self._transport.request("GET", f"/docker-deploy/templates/{template_id}")
        return DockerDeployTemplate.model_validate(_unwrap_template(data))


class AsyncDockerDeploy:
    """Asynchronous App Engine host API."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._transport = transport

    async def list_hosts(
        self, *, workspace_id: Optional[str] = None
    ) -> List[DockerDeployHost]:
        params = {"workspace_id": workspace_id} if workspace_id else None
        data = await self._transport.request("GET", "/docker-deploy/hosts", params=params)
        return [DockerDeployHost.model_validate(row) for row in _unwrap_hosts(data)]

    async def ensure_host(
        self,
        *,
        workspace_id: Optional[str] = None,
        external_workspace_id: Optional[str] = None,
    ) -> DockerDeployHost:
        data = await self._transport.request(
            "POST",
            "/docker-deploy/hosts/ensure",
            json_body=_ensure_body(
                workspace_id=workspace_id,
                external_workspace_id=external_workspace_id,
            ),
        )
        return DockerDeployHost.model_validate(_unwrap_host(data))

    async def get_host(self, host_id: str) -> DockerDeployHost:
        data = await self._transport.request("GET", f"/docker-deploy/hosts/{host_id}")
        return DockerDeployHost.model_validate(_unwrap_host(data))

    async def list_templates(self) -> List[DockerDeployTemplate]:
        data = await self._transport.request("GET", "/docker-deploy/templates")
        return [DockerDeployTemplate.model_validate(row) for row in _unwrap_templates(data)]

    async def get_template(self, template_id: str) -> DockerDeployTemplate:
        data = await self._transport.request("GET", f"/docker-deploy/templates/{template_id}")
        return DockerDeployTemplate.model_validate(_unwrap_template(data))
