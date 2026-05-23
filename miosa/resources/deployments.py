"""Deployments resource — sandbox→production publishing surface.

The Deployment is the stable production object; versions are immutable
publish results; domains route hostnames to versions; rollback repoints a
deployment at an older ready version.

See:
- ``docs-site/src/content/docs/deploy/overview.mdx`` for the product model
- ``miosa-compute/docs/deployments/api-sdk.md`` for the canonical contract

Backend phase status:
- ``list / get / create / update / delete / env`` map to the repo deployment
  surface.
- ``publish / versions.* / releases.* / rollback / domains.*`` map to the live
  release surface.
- ``runtime_instances.*`` maps to dynamic runtime status/log inspection.
- ``publish_from_sandbox`` maps to the direct sandbox -> deployment bridge.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..types import (
    Deployment,
    DeploymentBuild,
    DeploymentRelease,
    DeploymentVersion,
    PublishResult,
    RuntimeInstance,
)

if TYPE_CHECKING:  # pragma: no cover
    from .._http import AsyncTransport, SyncTransport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _attribution_kwargs(
    external_workspace_id: Optional[str],
    external_user_id: Optional[str],
    external_project_id: Optional[str],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if external_workspace_id is not None:
        out["external_workspace_id"] = external_workspace_id
    if external_user_id is not None:
        out["external_user_id"] = external_user_id
    if external_project_id is not None:
        out["external_project_id"] = external_project_id
    return out


def _idempotency_headers(key: Optional[str]) -> Dict[str, str]:
    return {"Idempotency-Key": key or uuid.uuid4().hex}


def _unwrap(data: Any) -> Any:
    """Most MIOSA endpoints wrap responses in ``{"data": ...}``."""
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data


# ---------------------------------------------------------------------------
# Sync — Versions sub-resource
# ---------------------------------------------------------------------------


class DeploymentVersions:
    """Version sub-resource scoped to a deployment ID."""

    def __init__(self, transport: "SyncTransport", deployment_id: str) -> None:
        self._transport = transport
        self._deployment_id = deployment_id

    def list(
        self,
        *,
        state: Optional[str] = None,
        external_workspace_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_project_id: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> List[DeploymentVersion]:
        params: Dict[str, Any] = {}
        if state is not None:
            params["state"] = state
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor
        params.update(
            _attribution_kwargs(
                external_workspace_id, external_user_id, external_project_id
            )
        )
        data = self._transport.request(
            "GET",
            f"/deployments/{self._deployment_id}/versions",
            params=params or None,
        )
        rows = _unwrap(data)
        if isinstance(rows, dict):
            rows = rows.get("items", rows.get("versions", []))
        return [DeploymentVersion.model_validate(r) for r in rows or []]

    def get(self, version_id: str) -> DeploymentVersion:
        data = self._transport.request(
            "GET",
            f"/deployments/{self._deployment_id}/versions/{version_id}",
        )
        return DeploymentVersion.model_validate(_unwrap(data))

    def promote(
        self,
        version_id: str,
        *,
        environment: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Deployment:
        body: Dict[str, Any] = {}
        if environment is not None:
            body["environment"] = environment
        data = self._transport.request(
            "POST",
            f"/deployments/{self._deployment_id}/versions/{version_id}/promote",
            json_body=body or None,
            headers=_idempotency_headers(idempotency_key),
        )
        return Deployment.model_validate(_unwrap(data))


class AsyncDeploymentVersions:
    """Async version sub-resource scoped to a deployment ID."""

    def __init__(self, transport: "AsyncTransport", deployment_id: str) -> None:
        self._transport = transport
        self._deployment_id = deployment_id

    async def list(
        self,
        *,
        state: Optional[str] = None,
        external_workspace_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_project_id: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> List[DeploymentVersion]:
        params: Dict[str, Any] = {}
        if state is not None:
            params["state"] = state
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor
        params.update(
            _attribution_kwargs(
                external_workspace_id, external_user_id, external_project_id
            )
        )
        data = await self._transport.request(
            "GET",
            f"/deployments/{self._deployment_id}/versions",
            params=params or None,
        )
        rows = _unwrap(data)
        if isinstance(rows, dict):
            rows = rows.get("items", rows.get("versions", []))
        return [DeploymentVersion.model_validate(r) for r in rows or []]

    async def get(self, version_id: str) -> DeploymentVersion:
        data = await self._transport.request(
            "GET",
            f"/deployments/{self._deployment_id}/versions/{version_id}",
        )
        return DeploymentVersion.model_validate(_unwrap(data))

    async def promote(
        self,
        version_id: str,
        *,
        environment: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Deployment:
        body: Dict[str, Any] = {}
        if environment is not None:
            body["environment"] = environment
        data = await self._transport.request(
            "POST",
            f"/deployments/{self._deployment_id}/versions/{version_id}/promote",
            json_body=body or None,
            headers=_idempotency_headers(idempotency_key),
        )
        return Deployment.model_validate(_unwrap(data))


# ---------------------------------------------------------------------------
# Sync / Async — Releases sub-resource
# ---------------------------------------------------------------------------


class DeploymentReleases:
    """Release sub-resource scoped to a deployment ID."""

    def __init__(self, transport: "SyncTransport", deployment_id: str) -> None:
        self._transport = transport
        self._deployment_id = deployment_id

    def list(self) -> List[DeploymentRelease]:
        data = self._transport.request(
            "GET", f"/deployments/{self._deployment_id}/releases"
        )
        rows = _unwrap(data)
        if isinstance(rows, dict):
            rows = rows.get("items", rows.get("releases", []))
        return [DeploymentRelease.model_validate(r) for r in rows or []]

    def get(self, release_id: str) -> DeploymentRelease:
        data = self._transport.request(
            "GET", f"/deployments/{self._deployment_id}/releases/{release_id}"
        )
        return DeploymentRelease.model_validate(_unwrap(data))


class AsyncDeploymentReleases:
    """Async release sub-resource scoped to a deployment ID."""

    def __init__(self, transport: "AsyncTransport", deployment_id: str) -> None:
        self._transport = transport
        self._deployment_id = deployment_id

    async def list(self) -> List[DeploymentRelease]:
        data = await self._transport.request(
            "GET", f"/deployments/{self._deployment_id}/releases"
        )
        rows = _unwrap(data)
        if isinstance(rows, dict):
            rows = rows.get("items", rows.get("releases", []))
        return [DeploymentRelease.model_validate(r) for r in rows or []]

    async def get(self, release_id: str) -> DeploymentRelease:
        data = await self._transport.request(
            "GET", f"/deployments/{self._deployment_id}/releases/{release_id}"
        )
        return DeploymentRelease.model_validate(_unwrap(data))


# ---------------------------------------------------------------------------
# Sync / Async — Runtime instance sub-resource
# ---------------------------------------------------------------------------


class DeploymentRuntimeInstances:
    """Runtime-instance sub-resource scoped to a deployment ID."""

    def __init__(self, transport: "SyncTransport", deployment_id: str) -> None:
        self._transport = transport
        self._deployment_id = deployment_id

    def list(self) -> List[RuntimeInstance]:
        data = self._transport.request(
            "GET", f"/deployments/{self._deployment_id}/runtime-instances"
        )
        rows = _unwrap(data)
        if isinstance(rows, dict):
            rows = rows.get("items", rows.get("runtime_instances", []))
        return [RuntimeInstance.model_validate(r) for r in rows or []]

    def get(self, instance_id: str) -> RuntimeInstance:
        data = self._transport.request(
            "GET",
            f"/deployments/{self._deployment_id}/runtime-instances/{instance_id}",
        )
        return RuntimeInstance.model_validate(_unwrap(data))

    def logs(self, instance_id: str, *, lines: int = 100) -> Dict[str, Any]:
        data = self._transport.request(
            "GET",
            f"/deployments/{self._deployment_id}/runtime-instances/{instance_id}/logs",
            params={"lines": lines},
        )
        return _unwrap(data)


class AsyncDeploymentRuntimeInstances:
    """Async runtime-instance sub-resource scoped to a deployment ID."""

    def __init__(self, transport: "AsyncTransport", deployment_id: str) -> None:
        self._transport = transport
        self._deployment_id = deployment_id

    async def list(self) -> List[RuntimeInstance]:
        data = await self._transport.request(
            "GET", f"/deployments/{self._deployment_id}/runtime-instances"
        )
        rows = _unwrap(data)
        if isinstance(rows, dict):
            rows = rows.get("items", rows.get("runtime_instances", []))
        return [RuntimeInstance.model_validate(r) for r in rows or []]

    async def get(self, instance_id: str) -> RuntimeInstance:
        data = await self._transport.request(
            "GET",
            f"/deployments/{self._deployment_id}/runtime-instances/{instance_id}",
        )
        return RuntimeInstance.model_validate(_unwrap(data))

    async def logs(self, instance_id: str, *, lines: int = 100) -> Dict[str, Any]:
        data = await self._transport.request(
            "GET",
            f"/deployments/{self._deployment_id}/runtime-instances/{instance_id}/logs",
            params={"lines": lines},
        )
        return _unwrap(data)


# ---------------------------------------------------------------------------
# Sync — Domains sub-resource
# ---------------------------------------------------------------------------


class DeploymentDomains:
    """Custom-domain sub-resource scoped to a deployment ID."""

    def __init__(self, transport: "SyncTransport", deployment_id: str) -> None:
        self._transport = transport
        self._deployment_id = deployment_id

    def add(
        self,
        domain: str,
        *,
        redirect_policy: Optional[str] = None,
        external_workspace_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_project_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"domain": domain}
        if redirect_policy is not None:
            body["redirect_policy"] = redirect_policy
        body.update(
            _attribution_kwargs(
                external_workspace_id, external_user_id, external_project_id
            )
        )
        data = self._transport.request(
            "POST",
            f"/deployments/{self._deployment_id}/domains",
            json_body=body,
            headers=_idempotency_headers(idempotency_key),
        )
        return _unwrap(data)

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._transport.request(
            "GET",
            f"/deployments/{self._deployment_id}/domains",
            params=params or None,
        )
        rows = _unwrap(data)
        if isinstance(rows, dict):
            rows = rows.get("items", rows.get("domains", []))
        return rows or []

    def verify(self, domain_id: str) -> Dict[str, Any]:
        data = self._transport.request(
            "POST",
            f"/deployments/{self._deployment_id}/domains/{domain_id}/verify",
        )
        return _unwrap(data)

    def delete(self, domain_id: str) -> None:
        self._transport.request(
            "DELETE",
            f"/deployments/{self._deployment_id}/domains/{domain_id}",
        )


class AsyncDeploymentDomains:
    """Async custom-domain sub-resource scoped to a deployment ID."""

    def __init__(self, transport: "AsyncTransport", deployment_id: str) -> None:
        self._transport = transport
        self._deployment_id = deployment_id

    async def add(
        self,
        domain: str,
        *,
        redirect_policy: Optional[str] = None,
        external_workspace_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_project_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"domain": domain}
        if redirect_policy is not None:
            body["redirect_policy"] = redirect_policy
        body.update(
            _attribution_kwargs(
                external_workspace_id, external_user_id, external_project_id
            )
        )
        data = await self._transport.request(
            "POST",
            f"/deployments/{self._deployment_id}/domains",
            json_body=body,
            headers=_idempotency_headers(idempotency_key),
        )
        return _unwrap(data)

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._transport.request(
            "GET",
            f"/deployments/{self._deployment_id}/domains",
            params=params or None,
        )
        rows = _unwrap(data)
        if isinstance(rows, dict):
            rows = rows.get("items", rows.get("domains", []))
        return rows or []

    async def verify(self, domain_id: str) -> Dict[str, Any]:
        data = await self._transport.request(
            "POST",
            f"/deployments/{self._deployment_id}/domains/{domain_id}/verify",
        )
        return _unwrap(data)

    async def delete(self, domain_id: str) -> None:
        await self._transport.request(
            "DELETE",
            f"/deployments/{self._deployment_id}/domains/{domain_id}",
        )


# ---------------------------------------------------------------------------
# Sync — top-level resource
# ---------------------------------------------------------------------------


class Deployments:
    """Synchronous Deployments resource.

    Usage::

        from miosa import Miosa

        miosa = Miosa(api_key="msk_live_...")

        # Publish from a sandbox
        result = miosa.deployments.publish(
            deployment_id=dep_id,
            source_sandbox_id=sandbox.id,
            kind="static",
            external_workspace_id="dental-office-123",
            external_user_id="dr-smith-456",
        )
        print(result.deployment.public_url)

        # Roll back
        miosa.deployments.rollback(dep_id, version_id="ver_...")

        # Custom domain
        miosa.deployments.domains(dep_id).add("smiledental.test")
    """

    def __init__(self, transport: "SyncTransport") -> None:
        self._transport = transport

    # -- collection --

    def list(
        self,
        *,
        project_id: Optional[str] = None,
        state: Optional[str] = None,
        external_workspace_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_project_id: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> List[Deployment]:
        params: Dict[str, Any] = {}
        if project_id is not None:
            params["project_id"] = project_id
        if state is not None:
            params["state"] = state
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor
        params.update(
            _attribution_kwargs(
                external_workspace_id, external_user_id, external_project_id
            )
        )
        data = self._transport.request(
            "GET", "/deployments", params=params or None
        )
        rows = _unwrap(data)
        if isinstance(rows, dict):
            rows = rows.get("items", rows.get("deployments", []))
        return [Deployment.model_validate(r) for r in rows or []]

    def get(self, deployment_id: str) -> Deployment:
        data = self._transport.request("GET", f"/deployments/{deployment_id}")
        return Deployment.model_validate(_unwrap(data))

    def create(
        self,
        *,
        name: str,
        project_id: Optional[str] = None,
        source_type: Optional[str] = None,
        repo_url: Optional[str] = None,
        branch: Optional[str] = None,
        build_command: Optional[str] = None,
        run_command: Optional[str] = None,
        auto_deploy: Optional[bool] = None,
        database: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        external_workspace_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_project_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Deployment:
        body: Dict[str, Any] = {"name": name}
        if repo_url is not None:
            body["repo_url"] = repo_url
        if branch is not None:
            body["branch"] = branch
        if build_command is not None:
            body["build_command"] = build_command
        if run_command is not None:
            body["run_command"] = run_command
        if auto_deploy is not None:
            body["auto_deploy"] = auto_deploy
        if database is not None:
            body["database"] = database
        if metadata is not None:
            body["metadata"] = metadata
        body.update(
            _attribution_kwargs(
                external_workspace_id, external_user_id, external_project_id
            )
        )

        data = self._transport.request(
            "POST",
            "/deployments",
            json_body=body,
            headers=_idempotency_headers(idempotency_key),
        )
        return Deployment.model_validate(_unwrap(data))

    def update(
        self,
        deployment_id: str,
        *,
        name: Optional[str] = None,
        branch: Optional[str] = None,
        build_command: Optional[str] = None,
        run_command: Optional[str] = None,
        auto_deploy: Optional[bool] = None,
        database: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        external_workspace_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_project_id: Optional[str] = None,
    ) -> Deployment:
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if branch is not None:
            body["branch"] = branch
        if build_command is not None:
            body["build_command"] = build_command
        if run_command is not None:
            body["run_command"] = run_command
        if auto_deploy is not None:
            body["auto_deploy"] = auto_deploy
        data = self._transport.request(
            "PATCH",
            f"/deployments/{deployment_id}",
            json_body=body or None,
        )
        return Deployment.model_validate(_unwrap(data))

    def delete(self, deployment_id: str) -> None:
        self._transport.request("DELETE", f"/deployments/{deployment_id}")

    # -- publish / rollback --

    def publish(
        self,
        deployment_id: str,
        *,
        source_sandbox_id: str,
        kind: str = "auto",
        environment: str = "production",
        output_path: Optional[str] = None,
        source_snapshot_path: Optional[str] = None,
        entrypoint: Optional[str] = None,
        promote: Optional[bool] = None,
        build_command: Optional[str] = None,
        run_command: Optional[str] = None,
        port: Optional[int] = None,
        health_check_path: Optional[str] = None,
        data_services: Optional[List[str]] = None,
        external_workspace_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_project_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> PublishResult:
        body: Dict[str, Any] = {
            "source_sandbox_id": source_sandbox_id,
        }
        if output_path is not None:
            body["output_path"] = output_path
        if entrypoint is not None:
            body["entrypoint"] = entrypoint
        if promote is not None:
            body["promote"] = promote
        data = self._transport.request(
            "POST",
            f"/deployments/{deployment_id}/publish",
            json_body=body,
            headers=_idempotency_headers(idempotency_key),
        )
        return PublishResult.model_validate(_unwrap(data))

    def publish_from_sandbox(
        self,
        sandbox_id: str,
        *,
        name: Optional[str] = None,
        deployment_id: Optional[str] = None,
        kind: str = "auto",
        environment: str = "production",
        output_path: Optional[str] = None,
        source_snapshot_path: Optional[str] = None,
        entrypoint: Optional[str] = None,
        domain: Optional[str] = None,
        custom_domain: Optional[str] = None,
        build_command: Optional[str] = None,
        run_command: Optional[str] = None,
        port: Optional[int] = None,
        health_check_path: Optional[str] = None,
        external_workspace_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_project_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Backward-compatible bridge: POST /sandboxes/:id/deploy.

        Returns the raw release-backed response from ``POST /sandboxes/:id/deploy``.
        Pass ``deployment_id`` to publish a new version to an existing
        deployment; otherwise pass ``name`` to create the stable deployment.
        """
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if deployment_id is not None:
            body["deployment_id"] = deployment_id
        if output_path is not None:
            body["output_path"] = output_path
        if source_snapshot_path is not None:
            body["source_snapshot_path"] = source_snapshot_path
        if entrypoint is not None:
            body["entrypoint"] = entrypoint
        if domain is not None:
            body["domain"] = domain
        if custom_domain is not None:
            body["custom_domain"] = custom_domain
        data = self._transport.request(
            "POST",
            f"/sandboxes/{sandbox_id}/deploy",
            json_body=body,
            headers=_idempotency_headers(idempotency_key),
        )
        return _unwrap(data)

    def rollback(
        self,
        deployment_id: str,
        *,
        version_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Deployment:
        body: Dict[str, Any] = {}
        if version_id is not None:
            body["version_id"] = version_id
        data = self._transport.request(
            "POST",
            f"/deployments/{deployment_id}/rollback",
            json_body=body or None,
            headers=_idempotency_headers(idempotency_key),
        )
        return Deployment.model_validate(_unwrap(data))

    def redeploy(
        self,
        deployment_id: str,
        *,
        idempotency_key: Optional[str] = None,
    ) -> Deployment:
        """Trigger a redeploy of an existing deployment (re-runs the last build)."""
        data = self._transport.request(
            "POST",
            f"/deployments/{deployment_id}/redeploy",
            json_body={},
            headers=_idempotency_headers(idempotency_key),
        )
        return Deployment.model_validate(_unwrap(data))

    def get_logs(
        self, deployment_id: str, *, lines: int = 100
    ) -> Dict[str, Any]:
        """Return recent log lines for a deployment."""
        data = self._transport.request(
            "GET",
            f"/deployments/{deployment_id}/logs",
            params={"lines": lines},
        )
        return _unwrap(data)

    # -- builds (legacy / repo-based flow) --

    def list_builds(
        self, deployment_id: str
    ) -> List[DeploymentBuild]:
        data = self._transport.request(
            "GET", f"/deployments/{deployment_id}/builds"
        )
        rows = _unwrap(data)
        if isinstance(rows, dict):
            rows = rows.get("items", rows.get("builds", []))
        return [DeploymentBuild.model_validate(r) for r in rows or []]

    def get_build(
        self, deployment_id: str, build_id: str
    ) -> DeploymentBuild:
        data = self._transport.request(
            "GET", f"/deployments/{deployment_id}/builds/{build_id}"
        )
        return DeploymentBuild.model_validate(_unwrap(data))

    # -- env --

    def list_env(self, deployment_id: str) -> List[Dict[str, Any]]:
        data = self._transport.request(
            "GET", f"/deployments/{deployment_id}/env"
        )
        rows = _unwrap(data)
        if isinstance(rows, dict):
            rows = rows.get("items", rows.get("env", []))
        return rows or []

    def set_env(
        self,
        deployment_id: str,
        vars: Dict[str, str],
        *,
        environment: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        body: Dict[str, Any] = {"env": vars}
        if environment is not None:
            body["environment"] = environment
        data = self._transport.request(
            "POST",
            f"/deployments/{deployment_id}/env",
            json_body=body,
        )
        rows = _unwrap(data)
        if isinstance(rows, dict):
            rows = rows.get("items", rows.get("env", []))
        return rows or []

    # -- sub-resources --

    def versions(self, deployment_id: str) -> DeploymentVersions:
        return DeploymentVersions(self._transport, deployment_id)

    def releases(self, deployment_id: str) -> DeploymentReleases:
        return DeploymentReleases(self._transport, deployment_id)

    def runtime_instances(self, deployment_id: str) -> DeploymentRuntimeInstances:
        return DeploymentRuntimeInstances(self._transport, deployment_id)

    def domains(self, deployment_id: str) -> DeploymentDomains:
        return DeploymentDomains(self._transport, deployment_id)


# ---------------------------------------------------------------------------
# Async — top-level resource
# ---------------------------------------------------------------------------


class AsyncDeployments:
    """Asynchronous Deployments resource. Mirrors :class:`Deployments`."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._transport = transport

    async def list(
        self,
        *,
        project_id: Optional[str] = None,
        state: Optional[str] = None,
        external_workspace_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_project_id: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> List[Deployment]:
        params: Dict[str, Any] = {}
        if project_id is not None:
            params["project_id"] = project_id
        if state is not None:
            params["state"] = state
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor
        params.update(
            _attribution_kwargs(
                external_workspace_id, external_user_id, external_project_id
            )
        )
        data = await self._transport.request(
            "GET", "/deployments", params=params or None
        )
        rows = _unwrap(data)
        if isinstance(rows, dict):
            rows = rows.get("items", rows.get("deployments", []))
        return [Deployment.model_validate(r) for r in rows or []]

    async def get(self, deployment_id: str) -> Deployment:
        data = await self._transport.request(
            "GET", f"/deployments/{deployment_id}"
        )
        return Deployment.model_validate(_unwrap(data))

    async def create(
        self,
        *,
        name: str,
        project_id: Optional[str] = None,
        source_type: Optional[str] = None,
        repo_url: Optional[str] = None,
        branch: Optional[str] = None,
        build_command: Optional[str] = None,
        run_command: Optional[str] = None,
        auto_deploy: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
        external_workspace_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_project_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Deployment:
        body: Dict[str, Any] = {"name": name}
        if repo_url is not None:
            body["repo_url"] = repo_url
        if branch is not None:
            body["branch"] = branch
        if build_command is not None:
            body["build_command"] = build_command
        if run_command is not None:
            body["run_command"] = run_command
        if auto_deploy is not None:
            body["auto_deploy"] = auto_deploy
        if database is not None:
            body["database"] = database
        if metadata is not None:
            body["metadata"] = metadata
        body.update(
            _attribution_kwargs(
                external_workspace_id, external_user_id, external_project_id
            )
        )
        data = await self._transport.request(
            "POST",
            "/deployments",
            json_body=body,
            headers=_idempotency_headers(idempotency_key),
        )
        return Deployment.model_validate(_unwrap(data))

    async def update(
        self,
        deployment_id: str,
        *,
        name: Optional[str] = None,
        branch: Optional[str] = None,
        build_command: Optional[str] = None,
        run_command: Optional[str] = None,
        auto_deploy: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
        external_workspace_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_project_id: Optional[str] = None,
    ) -> Deployment:
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if branch is not None:
            body["branch"] = branch
        if build_command is not None:
            body["build_command"] = build_command
        if run_command is not None:
            body["run_command"] = run_command
        if auto_deploy is not None:
            body["auto_deploy"] = auto_deploy
        data = await self._transport.request(
            "PATCH",
            f"/deployments/{deployment_id}",
            json_body=body or None,
        )
        return Deployment.model_validate(_unwrap(data))

    async def delete(self, deployment_id: str) -> None:
        await self._transport.request(
            "DELETE", f"/deployments/{deployment_id}"
        )

    async def publish(
        self,
        deployment_id: str,
        *,
        source_sandbox_id: str,
        kind: str = "auto",
        environment: str = "production",
        output_path: Optional[str] = None,
        source_snapshot_path: Optional[str] = None,
        entrypoint: Optional[str] = None,
        promote: Optional[bool] = None,
        build_command: Optional[str] = None,
        run_command: Optional[str] = None,
        port: Optional[int] = None,
        health_check_path: Optional[str] = None,
        data_services: Optional[List[str]] = None,
        external_workspace_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_project_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> PublishResult:
        body: Dict[str, Any] = {
            "source_sandbox_id": source_sandbox_id,
        }
        if output_path is not None:
            body["output_path"] = output_path
        if entrypoint is not None:
            body["entrypoint"] = entrypoint
        if promote is not None:
            body["promote"] = promote
        data = await self._transport.request(
            "POST",
            f"/deployments/{deployment_id}/publish",
            json_body=body,
            headers=_idempotency_headers(idempotency_key),
        )
        return PublishResult.model_validate(_unwrap(data))

    async def publish_from_sandbox(
        self,
        sandbox_id: str,
        *,
        name: Optional[str] = None,
        deployment_id: Optional[str] = None,
        kind: str = "auto",
        environment: str = "production",
        output_path: Optional[str] = None,
        source_snapshot_path: Optional[str] = None,
        entrypoint: Optional[str] = None,
        domain: Optional[str] = None,
        custom_domain: Optional[str] = None,
        build_command: Optional[str] = None,
        run_command: Optional[str] = None,
        port: Optional[int] = None,
        health_check_path: Optional[str] = None,
        external_workspace_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_project_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if deployment_id is not None:
            body["deployment_id"] = deployment_id
        if output_path is not None:
            body["output_path"] = output_path
        if source_snapshot_path is not None:
            body["source_snapshot_path"] = source_snapshot_path
        if entrypoint is not None:
            body["entrypoint"] = entrypoint
        if domain is not None:
            body["domain"] = domain
        if custom_domain is not None:
            body["custom_domain"] = custom_domain
        data = await self._transport.request(
            "POST",
            f"/sandboxes/{sandbox_id}/deploy",
            json_body=body,
            headers=_idempotency_headers(idempotency_key),
        )
        return _unwrap(data)

    async def rollback(
        self,
        deployment_id: str,
        *,
        version_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Deployment:
        body: Dict[str, Any] = {}
        if version_id is not None:
            body["version_id"] = version_id
        data = await self._transport.request(
            "POST",
            f"/deployments/{deployment_id}/rollback",
            json_body=body or None,
            headers=_idempotency_headers(idempotency_key),
        )
        return Deployment.model_validate(_unwrap(data))

    async def redeploy(
        self,
        deployment_id: str,
        *,
        idempotency_key: Optional[str] = None,
    ) -> Deployment:
        """Trigger a redeploy of an existing deployment (re-runs the last build)."""
        data = await self._transport.request(
            "POST",
            f"/deployments/{deployment_id}/redeploy",
            json_body={},
            headers=_idempotency_headers(idempotency_key),
        )
        return Deployment.model_validate(_unwrap(data))

    async def get_logs(
        self, deployment_id: str, *, lines: int = 100
    ) -> Dict[str, Any]:
        """Return recent log lines for a deployment."""
        data = await self._transport.request(
            "GET",
            f"/deployments/{deployment_id}/logs",
            params={"lines": lines},
        )
        return _unwrap(data)

    async def list_builds(
        self, deployment_id: str
    ) -> List[DeploymentBuild]:
        data = await self._transport.request(
            "GET", f"/deployments/{deployment_id}/builds"
        )
        rows = _unwrap(data)
        if isinstance(rows, dict):
            rows = rows.get("items", rows.get("builds", []))
        return [DeploymentBuild.model_validate(r) for r in rows or []]

    async def get_build(
        self, deployment_id: str, build_id: str
    ) -> DeploymentBuild:
        data = await self._transport.request(
            "GET", f"/deployments/{deployment_id}/builds/{build_id}"
        )
        return DeploymentBuild.model_validate(_unwrap(data))

    async def list_env(self, deployment_id: str) -> List[Dict[str, Any]]:
        data = await self._transport.request(
            "GET", f"/deployments/{deployment_id}/env"
        )
        rows = _unwrap(data)
        if isinstance(rows, dict):
            rows = rows.get("items", rows.get("env", []))
        return rows or []

    async def set_env(
        self,
        deployment_id: str,
        vars: Dict[str, str],
        *,
        environment: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        body: Dict[str, Any] = {"env": vars}
        if environment is not None:
            body["environment"] = environment
        data = await self._transport.request(
            "POST",
            f"/deployments/{deployment_id}/env",
            json_body=body,
        )
        rows = _unwrap(data)
        if isinstance(rows, dict):
            rows = rows.get("items", rows.get("env", []))
        return rows or []

    def versions(
        self, deployment_id: str
    ) -> AsyncDeploymentVersions:
        return AsyncDeploymentVersions(self._transport, deployment_id)

    def releases(
        self, deployment_id: str
    ) -> AsyncDeploymentReleases:
        return AsyncDeploymentReleases(self._transport, deployment_id)

    def runtime_instances(
        self, deployment_id: str
    ) -> AsyncDeploymentRuntimeInstances:
        return AsyncDeploymentRuntimeInstances(self._transport, deployment_id)

    def domains(
        self, deployment_id: str
    ) -> AsyncDeploymentDomains:
        return AsyncDeploymentDomains(self._transport, deployment_id)


__all__ = [
    "AsyncDeploymentDomains",
    "AsyncDeploymentReleases",
    "AsyncDeploymentRuntimeInstances",
    "AsyncDeploymentVersions",
    "AsyncDeployments",
    "DeploymentDomains",
    "DeploymentReleases",
    "DeploymentRuntimeInstances",
    "DeploymentVersions",
    "Deployments",
]
