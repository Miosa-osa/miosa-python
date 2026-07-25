"""MIOSA Connect — provider connectors and runtime tokens.

Connect is the product-facing credential layer. Egress remains the runtime
enforcement layer underneath it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from urllib.parse import quote

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data", "binding")) -> Any:
    if isinstance(data, dict):
        for key in keys:
            if key in data:
                return data[key]
    return data


def _unwrap_list(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "connectors", "items"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    return []


def _compact(body: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in body.items() if value is not None}


def _connector_path(connector: str) -> str:
    return quote(connector, safe="")


def _external_attribution(attrs: Dict[str, Any]) -> Dict[str, Any]:
    return _compact(
        {
            "external_user_id": attrs.get("external_user_id")
            or attrs.get("externalUserId"),
            "external_workspace_id": attrs.get("external_workspace_id")
            or attrs.get("externalWorkspaceId"),
            "external_project_id": attrs.get("external_project_id")
            or attrs.get("externalProjectId"),
        }
    )


def _create_body(provider: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
    credential = attrs.get("credential")
    if isinstance(credential, dict):
        value = (
            attrs.get("value")
            or attrs.get("token")
            or attrs.get("api_key")
            or credential.get("value")
        )
        credential_body = {
            key: val
            for key, val in credential.items()
            if key not in {"field", "value"}
        }
        credential_body["field"] = credential.get("field", "api_key")
        credential_body["value"] = value
    else:
        value = attrs.get("value") or attrs.get("token") or attrs.get("api_key")
        credential_body = {"field": "api_key", "value": value} if value else None

    uid = attrs.get("uid") or f"{provider}/{attrs.get('name', 'default')}"

    return _compact(
        {
            "provider": provider,
            "type": str(attrs.get("type", "api_key")).replace("-", "_"),
            "name": attrs.get("name"),
            "uid": uid,
            "scope": attrs.get("scope"),
            "workspace_id": attrs.get("workspace_id") or attrs.get("workspaceId"),
            "owner_user_id": attrs.get("owner_user_id") or attrs.get("ownerUserId"),
            **_external_attribution(attrs),
            "credential": credential_body,
        }
    )


def _token_body(**params: Any) -> Dict[str, Any]:
    return _compact(
        {
            "subject": params.get("subject") or {"type": "app"},
            "installation_id": params.get("installation_id")
            or params.get("installationId"),
            "project_id": params.get("project_id") or params.get("projectId"),
            "environment": params.get("environment"),
            "resource_type": params.get("resource_type") or params.get("resourceType"),
            "resource_id": params.get("resource_id") or params.get("resourceId"),
            "scopes": params.get("scopes") or params.get("scope"),
            "audience": params.get("audience"),
            **_external_attribution(params),
            "validity_buffer_ms": params.get("validity_buffer_ms")
            or params.get("validityBufferMs"),
        }
    )


def _link_filters(**filters: Any) -> Dict[str, Any]:
    return _compact(
        {
            "workspace_id": filters.get("workspace_id") or filters.get("workspaceId"),
            "project_id": filters.get("project_id") or filters.get("projectId"),
            "connector_id": filters.get("connector_id") or filters.get("connectorId"),
            "environment": filters.get("environment"),
            "status": filters.get("status"),
            **_external_attribution(filters),
        }
    )


def _default_filters(**filters: Any) -> Dict[str, Any]:
    params = _link_filters(**filters)
    params.update(
        _compact(
            {
                "default_scope": filters.get("default_scope")
                or filters.get("defaultScope"),
                "target": filters.get("target"),
            }
        )
    )
    return params


def _applicable_default_filters(**filters: Any) -> Dict[str, Any]:
    return _compact(
        {
            "workspace_id": filters.get("workspace_id") or filters.get("workspaceId"),
            "project_id": filters.get("project_id") or filters.get("projectId"),
            "environment": filters.get("environment"),
            "target": filters.get("target"),
            "resource_type": filters.get("resource_type") or filters.get("resourceType"),
            "resource_id": filters.get("resource_id") or filters.get("resourceId"),
            **_external_attribution(filters),
        }
    )


def _materialize_default_body(**attrs: Any) -> Dict[str, Any]:
    return _compact(
        {
            "workspace_id": attrs.get("workspace_id") or attrs.get("workspaceId"),
            "project_id": attrs.get("project_id") or attrs.get("projectId"),
            "environment": attrs.get("environment"),
            "target": attrs.get("target"),
            "resource_type": attrs.get("resource_type") or attrs.get("resourceType"),
            "resource_id": attrs.get("resource_id") or attrs.get("resourceId"),
            "env_name": attrs.get("env_name") or attrs.get("envName"),
            **_external_attribution(attrs),
        }
    )


def _oauth_start_body(**attrs: Any) -> Dict[str, Any]:
    return _compact(
        {
            "provider": attrs.get("provider"),
            "scope": attrs.get("scope"),
            "expose_as_env": attrs.get("expose_as_env") if "expose_as_env" in attrs else attrs.get("exposeAsEnv"),
            "owner_user_id": attrs.get("owner_user_id") or attrs.get("ownerUserId"),
            **_external_attribution(attrs),
        }
    )


def _project_link_body(**attrs: Any) -> Dict[str, Any]:
    mode = attrs.get("mode")

    return _compact(
        {
            "connector": attrs.get("connector"),
            "connector_id": attrs.get("connector_id") or attrs.get("connectorId"),
            "installation_id": attrs.get("installation_id") or attrs.get("installationId"),
            "workspace_id": attrs.get("workspace_id") or attrs.get("workspaceId"),
            "project_id": attrs.get("project_id") or attrs.get("projectId"),
            "environment": attrs.get("environment"),
            "resource_type": attrs.get("resource_type") or attrs.get("resourceType"),
            "resource_id": attrs.get("resource_id") or attrs.get("resourceId"),
            "allowed_subjects": attrs.get("allowed_subjects") or attrs.get("allowedSubjects"),
            "allowed_scopes": attrs.get("allowed_scopes") or attrs.get("allowedScopes"),
            "mode": mode.replace("-", "_") if isinstance(mode, str) else mode,
            "effect": attrs.get("effect"),
            **_external_attribution(attrs),
            "metadata": attrs.get("metadata"),
        }
    )


def _default_body(**attrs: Any) -> Dict[str, Any]:
    body = _project_link_body(**attrs)
    body.update(
        _compact(
            {
                "default_scope": attrs.get("default_scope")
                or attrs.get("defaultScope"),
                "target": attrs.get("target"),
            }
        )
    )
    return body


def _trigger_body(**attrs: Any) -> Dict[str, Any]:
    return _compact(
        {
            "connector": attrs.get("connector"),
            "connector_id": attrs.get("connector_id") or attrs.get("connectorId"),
            "workspace_id": attrs.get("workspace_id") or attrs.get("workspaceId"),
            "project_id": attrs.get("project_id") or attrs.get("projectId"),
            "environment": attrs.get("environment"),
            "destination_path": attrs.get("destination_path")
            or attrs.get("destinationPath"),
            "destination_url": attrs.get("destination_url") or attrs.get("destinationUrl"),
            "event_types": attrs.get("event_types") or attrs.get("eventTypes"),
            "status": attrs.get("status"),
            "provider_adapter": attrs.get("provider_adapter")
            or attrs.get("providerAdapter"),
            "webhook_signing_secret": attrs.get("webhook_signing_secret")
            or attrs.get("webhookSigningSecret"),
            **_external_attribution(attrs),
            "metadata": attrs.get("metadata"),
        }
    )


def _trigger_delivery_filters(**filters: Any) -> Dict[str, Any]:
    params = _link_filters(**filters)
    params.update(
        _compact(
            {
                "trigger_id": filters.get("trigger_id") or filters.get("triggerId"),
                "event_type": filters.get("event_type") or filters.get("eventType"),
            }
        )
    )
    return params


class Connectors:
    """Provider connectors and runtime token requests."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        """List Connect provider connectors visible to the current caller."""
        params = _compact(
            {
                "scope": filters.get("scope"),
                "workspace_id": filters.get("workspace_id")
                or filters.get("workspaceId"),
                "owner_user_id": filters.get("owner_user_id")
                or filters.get("ownerUserId"),
                "external_user_id": filters.get("external_user_id")
                or filters.get("externalUserId"),
                "external_workspace_id": filters.get("external_workspace_id")
                or filters.get("externalWorkspaceId"),
                "external_project_id": filters.get("external_project_id")
                or filters.get("externalProjectId"),
            }
        )
        data = self._t.request(
            "GET", "/connect/connectors", params=params or None
        )
        return _unwrap_list(data)

    def get(self, connector: str) -> Dict[str, Any]:
        """Show a connector by UID or id."""
        return _unwrap(
            self._t.request("GET", f"/connect/connectors/{_connector_path(connector)}")
        )

    show = get

    def create(self, provider: str, **attrs: Any) -> Dict[str, Any]:
        """Create an API-key backed connector."""
        return _unwrap(
            self._t.request(
                "POST",
                "/connect/connectors",
                json_body=_create_body(provider, attrs),
            )
        )

    def get_token(self, connector: str, **params: Any) -> Dict[str, Any]:
        """Request a runtime provider token for a connector."""
        return _unwrap(
            self._t.request(
                "POST",
                f"/connect/token/{_connector_path(connector)}",
                json_body=_token_body(**params),
            )
        )

    token = get_token

    def oauth_providers(self) -> List[Dict[str, Any]]:
        """List OAuth app providers available for end-user authorization."""
        data = self._t.request("GET", "/connect/oauth/providers")
        return _unwrap_list(data)

    def start_oauth(self, provider: str, **attrs: Any) -> Dict[str, Any]:
        """Start an OAuth authorization flow for a provider-backed connector."""
        return _unwrap(
            self._t.request(
                "POST",
                "/connect/oauth/start",
                json_body=_oauth_start_body(provider=provider, **attrs),
            )
        )

    def installations(self, **filters: Any) -> List[Dict[str, Any]]:
        """List connector installations/grants."""
        data = self._t.request(
            "GET", "/connect/installations", params=_link_filters(**filters) or None
        )
        return _unwrap_list(data)

    def project_links(self, **filters: Any) -> List[Dict[str, Any]]:
        """List project/environment connector links."""
        data = self._t.request(
            "GET", "/connect/project-links", params=_link_filters(**filters) or None
        )
        return _unwrap_list(data)

    def defaults(self, **filters: Any) -> List[Dict[str, Any]]:
        """List inherited connector defaults for tenant/workspace/project runtimes."""
        data = self._t.request(
            "GET", "/connect/defaults", params=_default_filters(**filters) or None
        )
        return _unwrap_list(data)

    def applicable_defaults(self, **filters: Any) -> List[Dict[str, Any]]:
        """Resolve inherited connector defaults that apply to a runtime target."""
        data = self._t.request(
            "GET",
            "/connect/defaults/applicable",
            params=_applicable_default_filters(**filters) or None,
        )
        return _unwrap_list(data)

    def materialize_defaults(self, **attrs: Any) -> Dict[str, Any]:
        """Materialize inherited connector defaults onto one runtime resource."""
        return _unwrap(
            self._t.request(
                "POST",
                "/connect/defaults/materialize",
                json_body=_materialize_default_body(**attrs),
            )
        )

    def create_default(self, **attrs: Any) -> Dict[str, Any]:
        """Create an inherited connector default for future runtime resources."""
        return _unwrap(
            self._t.request(
                "POST",
                "/connect/defaults",
                json_body=_default_body(**attrs),
            )
        )

    def delete_default(self, default_id: str) -> None:
        """Delete an inherited connector default."""
        self._t.request("DELETE", f"/connect/defaults/{_connector_path(default_id)}")

    def triggers(self, **filters: Any) -> List[Dict[str, Any]]:
        """List inbound connector trigger forwarding definitions."""
        data = self._t.request(
            "GET", "/connect/triggers", params=_link_filters(**filters) or None
        )
        return _unwrap_list(data)

    def create_trigger(self, **attrs: Any) -> Dict[str, Any]:
        """Create an inbound connector trigger forwarding definition."""
        return _unwrap(
            self._t.request(
                "POST",
                "/connect/triggers",
                json_body=_trigger_body(**attrs),
            )
        )

    def trigger_deliveries(self, **filters: Any) -> List[Dict[str, Any]]:
        """List inbound provider trigger delivery attempts."""
        data = self._t.request(
            "GET",
            "/connect/trigger-deliveries",
            params=_trigger_delivery_filters(**filters) or None,
        )
        return _unwrap_list(data)

    def trigger_delivery_history(self, trigger_id: str) -> List[Dict[str, Any]]:
        """List delivery attempts for one trigger."""
        data = self._t.request(
            "GET", f"/connect/triggers/{_connector_path(trigger_id)}/deliveries"
        )
        return _unwrap_list(data)

    def delete_trigger(self, trigger_id: str) -> None:
        """Delete an inbound connector trigger forwarding definition."""
        self._t.request("DELETE", f"/connect/triggers/{_connector_path(trigger_id)}")

    def create_project_link(self, **attrs: Any) -> Dict[str, Any]:
        """Link a connector to a project/environment/resource."""
        return _unwrap(
            self._t.request(
                "POST",
                "/connect/project-links",
                json_body=_project_link_body(**attrs),
            )
        )

    def delete_project_link(self, link_id: str) -> None:
        """Delete a project connector link."""
        self._t.request("DELETE", f"/connect/project-links/{_connector_path(link_id)}")


class AsyncConnectors:
    """Async provider connectors and runtime token requests."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = _compact(
            {
                "scope": filters.get("scope"),
                "workspace_id": filters.get("workspace_id")
                or filters.get("workspaceId"),
                "owner_user_id": filters.get("owner_user_id")
                or filters.get("ownerUserId"),
                "external_user_id": filters.get("external_user_id")
                or filters.get("externalUserId"),
                "external_workspace_id": filters.get("external_workspace_id")
                or filters.get("externalWorkspaceId"),
                "external_project_id": filters.get("external_project_id")
                or filters.get("externalProjectId"),
            }
        )
        data = await self._t.request(
            "GET", "/connect/connectors", params=params or None
        )
        return _unwrap_list(data)

    async def get(self, connector: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "GET", f"/connect/connectors/{_connector_path(connector)}"
            )
        )

    show = get

    async def create(self, provider: str, **attrs: Any) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                "/connect/connectors",
                json_body=_create_body(provider, attrs),
            )
        )

    async def get_token(self, connector: str, **params: Any) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                f"/connect/token/{_connector_path(connector)}",
                json_body=_token_body(**params),
            )
        )

    token = get_token

    async def oauth_providers(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", "/connect/oauth/providers")
        return _unwrap_list(data)

    async def start_oauth(self, provider: str, **attrs: Any) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                "/connect/oauth/start",
                json_body=_oauth_start_body(provider=provider, **attrs),
            )
        )

    async def installations(self, **filters: Any) -> List[Dict[str, Any]]:
        data = await self._t.request(
            "GET", "/connect/installations", params=_link_filters(**filters) or None
        )
        return _unwrap_list(data)

    async def project_links(self, **filters: Any) -> List[Dict[str, Any]]:
        data = await self._t.request(
            "GET", "/connect/project-links", params=_link_filters(**filters) or None
        )
        return _unwrap_list(data)

    async def defaults(self, **filters: Any) -> List[Dict[str, Any]]:
        data = await self._t.request(
            "GET", "/connect/defaults", params=_default_filters(**filters) or None
        )
        return _unwrap_list(data)

    async def applicable_defaults(self, **filters: Any) -> List[Dict[str, Any]]:
        data = await self._t.request(
            "GET",
            "/connect/defaults/applicable",
            params=_applicable_default_filters(**filters) or None,
        )
        return _unwrap_list(data)

    async def materialize_defaults(self, **attrs: Any) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                "/connect/defaults/materialize",
                json_body=_materialize_default_body(**attrs),
            )
        )

    async def create_default(self, **attrs: Any) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                "/connect/defaults",
                json_body=_default_body(**attrs),
            )
        )

    async def delete_default(self, default_id: str) -> None:
        await self._t.request("DELETE", f"/connect/defaults/{_connector_path(default_id)}")

    async def triggers(self, **filters: Any) -> List[Dict[str, Any]]:
        data = await self._t.request(
            "GET", "/connect/triggers", params=_link_filters(**filters) or None
        )
        return _unwrap_list(data)

    async def create_trigger(self, **attrs: Any) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                "/connect/triggers",
                json_body=_trigger_body(**attrs),
            )
        )

    async def trigger_deliveries(self, **filters: Any) -> List[Dict[str, Any]]:
        data = await self._t.request(
            "GET",
            "/connect/trigger-deliveries",
            params=_trigger_delivery_filters(**filters) or None,
        )
        return _unwrap_list(data)

    async def trigger_delivery_history(self, trigger_id: str) -> List[Dict[str, Any]]:
        data = await self._t.request(
            "GET", f"/connect/triggers/{_connector_path(trigger_id)}/deliveries"
        )
        return _unwrap_list(data)

    async def delete_trigger(self, trigger_id: str) -> None:
        await self._t.request("DELETE", f"/connect/triggers/{_connector_path(trigger_id)}")

    async def create_project_link(self, **attrs: Any) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                "/connect/project-links",
                json_body=_project_link_body(**attrs),
            )
        )

    async def delete_project_link(self, link_id: str) -> None:
        await self._t.request("DELETE", f"/connect/project-links/{_connector_path(link_id)}")


class _RuntimeConnectors:
    """Runtime-scoped Connect provider bindings."""

    def __init__(self, transport: "SyncTransport", base_path: str) -> None:
        self._t = transport
        self._base_path = base_path

    def list(self) -> List[Dict[str, Any]]:
        data = self._t.request("GET", self._base_path)
        return _unwrap_list(data)

    def attach(
        self,
        connector: str,
        *,
        env: str,
        mode: Optional[str] = "brokered-env",
        installation_id: Optional[str] = None,
        installationId: Optional[str] = None,  # noqa: N803 - API compatibility alias
        **kwargs: Any,
    ) -> Dict[str, Any]:
        body = _compact(
            {
                "connector": connector,
                "env_name": env,
                "mode": mode.replace("-", "_") if mode else None,
                "installation_id": installation_id or installationId,
                "project_id": kwargs.get("project_id") or kwargs.get("projectId"),
                "environment": kwargs.get("environment"),
                **_external_attribution(kwargs),
            }
        )
        return _unwrap(
            self._t.request(
                "POST",
                self._base_path,
                json_body=body,
            )
        )

    def detach(self, binding_or_connector: str) -> None:
        self._t.request(
            "DELETE",
            f"{self._base_path}/{_connector_path(binding_or_connector)}",
        )

    def sync(self) -> Dict[str, Any]:
        return _unwrap(
            self._t.request(
                "POST", f"{self._base_path}/sync", json_body={}
            )
        )

    def preflight(self, **params: Any) -> Dict[str, Any]:
        return _unwrap(
            self._t.request(
                "POST",
                f"{self._base_path}/preflight",
                json_body=_compact(params),
            )
        )


class SandboxConnectors(_RuntimeConnectors):
    """Sandbox-scoped Connect provider bindings."""

    def __init__(self, transport: "SyncTransport", sandbox_id: str) -> None:
        super().__init__(transport, f"/sandboxes/{sandbox_id}/connectors")


class ComputerConnectors(_RuntimeConnectors):
    """Computer-scoped Connect provider bindings."""

    def __init__(self, transport: "SyncTransport", computer_id: str) -> None:
        super().__init__(transport, f"/computers/{computer_id}/connectors")


class DeploymentConnectors(_RuntimeConnectors):
    """Deployment-scoped Connect provider bindings."""

    def __init__(self, transport: "SyncTransport", deployment_id: str) -> None:
        super().__init__(transport, f"/deployments/{deployment_id}/connectors")


class _AsyncRuntimeConnectors:
    """Async runtime-scoped Connect provider bindings."""

    def __init__(self, transport: "AsyncTransport", base_path: str) -> None:
        self._t = transport
        self._base_path = base_path

    async def list(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", self._base_path)
        return _unwrap_list(data)

    async def attach(
        self,
        connector: str,
        *,
        env: str,
        mode: Optional[str] = "brokered-env",
        installation_id: Optional[str] = None,
        installationId: Optional[str] = None,  # noqa: N803 - API compatibility alias
        **kwargs: Any,
    ) -> Dict[str, Any]:
        body = _compact(
            {
                "connector": connector,
                "env_name": env,
                "mode": mode.replace("-", "_") if mode else None,
                "installation_id": installation_id or installationId,
                "project_id": kwargs.get("project_id") or kwargs.get("projectId"),
                "environment": kwargs.get("environment"),
                **_external_attribution(kwargs),
            }
        )
        return _unwrap(
            await self._t.request(
                "POST",
                self._base_path,
                json_body=body,
            )
        )

    async def detach(self, binding_or_connector: str) -> None:
        await self._t.request(
            "DELETE",
            f"{self._base_path}/{_connector_path(binding_or_connector)}",
        )

    async def sync(self) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST", f"{self._base_path}/sync", json_body={}
            )
        )

    async def preflight(self, **params: Any) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                f"{self._base_path}/preflight",
                json_body=_compact(params),
            )
        )


class AsyncSandboxConnectors(_AsyncRuntimeConnectors):
    """Async sandbox-scoped Connect provider bindings."""

    def __init__(self, transport: "AsyncTransport", sandbox_id: str) -> None:
        super().__init__(transport, f"/sandboxes/{sandbox_id}/connectors")


class AsyncComputerConnectors(_AsyncRuntimeConnectors):
    """Async computer-scoped Connect provider bindings."""

    def __init__(self, transport: "AsyncTransport", computer_id: str) -> None:
        super().__init__(transport, f"/computers/{computer_id}/connectors")


class AsyncDeploymentConnectors(_AsyncRuntimeConnectors):
    """Async deployment-scoped Connect provider bindings."""

    def __init__(self, transport: "AsyncTransport", deployment_id: str) -> None:
        super().__init__(transport, f"/deployments/{deployment_id}/connectors")
