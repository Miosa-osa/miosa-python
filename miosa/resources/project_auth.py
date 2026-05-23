"""Project auth — built-in auth for sandboxes and deployments."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(
    data: Any,
    keys: tuple[str, ...] = ("data", "project_auth", "config", "items"),
) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class ProjectAuth:
    """Project Auth — built-in auth for generated apps inside sandboxes/deployments."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def status(self, resource_type: str, resource_id: str) -> Dict[str, Any]:
        """Get the current project-auth status and config."""
        return _unwrap(
            self._t.request(
                "GET",
                "/project-auth/status",
                params=_resource_params(resource_type, resource_id),
            )
        )

    def enable(
        self,
        resource_type: str,
        resource_id: str,
        *,
        config: Optional[Dict[str, Any]] = None,
        **config_overrides: Any,
    ) -> Dict[str, Any]:
        """Enable project auth."""
        body = _resource_body(resource_type, resource_id, config, config_overrides)
        return _unwrap(
            self._t.request(
                "POST", "/project-auth/enable", json_body=body
            )
        )

    def disable(self, resource_type: str, resource_id: str) -> Dict[str, Any]:
        """Disable project auth."""
        return _unwrap(
            self._t.request(
                "POST",
                "/project-auth/disable",
                json_body=_resource_params(resource_type, resource_id),
            )
        )

    def update(
        self,
        resource_type: str,
        resource_id: str,
        *,
        config: Optional[Dict[str, Any]] = None,
        **config_overrides: Any,
    ) -> Dict[str, Any]:
        """Update project-auth configuration."""
        body = _resource_body(resource_type, resource_id, config, config_overrides)
        return _unwrap(
            self._t.request("PATCH", "/project-auth/config", json_body=body)
        )


class AsyncProjectAuth:
    """Async project auth."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def status(self, resource_type: str, resource_id: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "GET",
                "/project-auth/status",
                params=_resource_params(resource_type, resource_id),
            )
        )

    async def enable(
        self,
        resource_type: str,
        resource_id: str,
        *,
        config: Optional[Dict[str, Any]] = None,
        **config_overrides: Any,
    ) -> Dict[str, Any]:
        body = _resource_body(resource_type, resource_id, config, config_overrides)
        return _unwrap(
            await self._t.request(
                "POST", "/project-auth/enable", json_body=body
            )
        )

    async def disable(self, resource_type: str, resource_id: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                "/project-auth/disable",
                json_body=_resource_params(resource_type, resource_id),
            )
        )

    async def update(
        self,
        resource_type: str,
        resource_id: str,
        *,
        config: Optional[Dict[str, Any]] = None,
        **config_overrides: Any,
    ) -> Dict[str, Any]:
        body = _resource_body(resource_type, resource_id, config, config_overrides)
        return _unwrap(
            await self._t.request(
                "PATCH", "/project-auth/config", json_body=body
            )
        )


def _resource_params(resource_type: str, resource_id: str) -> Dict[str, str]:
    if not resource_type or not resource_id:
        raise ValueError("project auth requires resource_type and resource_id")
    return {"resource_type": resource_type, "resource_id": resource_id}


def _resource_body(
    resource_type: str,
    resource_id: str,
    config: Optional[Dict[str, Any]],
    config_overrides: Dict[str, Any],
) -> Dict[str, Any]:
    body = _resource_params(resource_type, resource_id)
    merged = dict(config or {})
    merged.update({k: v for k, v in config_overrides.items() if v is not None})
    body["config"] = merged
    return body
