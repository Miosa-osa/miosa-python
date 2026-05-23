"""Sandbox templates — CRUD, build-spec schema, builds."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data", "templates", "builds", "items")) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class SandboxTemplates:
    """Tenant-level sandbox template management."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, *, include_aliases: bool = False) -> List[Dict[str, Any]]:
        params = {"include_aliases": include_aliases} if include_aliases else None
        data = self._t.request("GET", "/sandbox-templates", params=params)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def get(self, template_id: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("GET", f"/sandbox-templates/{template_id}"))

    def create(self, *, name: str, build_spec: Dict[str, Any], **attrs: Any) -> Dict[str, Any]:
        body = {
            "name": name,
            "build_spec": build_spec,
            **{k: v for k, v in attrs.items() if v is not None},
        }
        return _unwrap(self._t.request("POST", "/sandbox-templates", json_body=body))

    def build_spec_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for build specs."""
        return self._t.request("GET", "/sandbox-templates/build-spec")

    def validate(self, build_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a build spec without creating a template."""
        return self._t.request(
            "POST", "/sandbox-templates/validate", json_body={"build_spec": build_spec}
        )

    def list_builds(self, template_id: str) -> List[Dict[str, Any]]:
        data = self._t.request("GET", f"/sandbox-templates/{template_id}/builds")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def create_build(self, template_id: str, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            self._t.request(
                "POST", f"/sandbox-templates/{template_id}/builds", json_body=body
            )
        )


class AsyncSandboxTemplates:
    """Async sandbox templates."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self, *, include_aliases: bool = False) -> List[Dict[str, Any]]:
        params = {"include_aliases": include_aliases} if include_aliases else None
        data = await self._t.request("GET", "/sandbox-templates", params=params)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def get(self, template_id: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request("GET", f"/sandbox-templates/{template_id}")
        )

    async def create(
        self, *, name: str, build_spec: Dict[str, Any], **attrs: Any
    ) -> Dict[str, Any]:
        body = {
            "name": name,
            "build_spec": build_spec,
            **{k: v for k, v in attrs.items() if v is not None},
        }
        return _unwrap(
            await self._t.request("POST", "/sandbox-templates", json_body=body)
        )

    async def build_spec_schema(self) -> Dict[str, Any]:
        return await self._t.request("GET", "/sandbox-templates/build-spec")

    async def validate(self, build_spec: Dict[str, Any]) -> Dict[str, Any]:
        return await self._t.request(
            "POST", "/sandbox-templates/validate", json_body={"build_spec": build_spec}
        )

    async def list_builds(self, template_id: str) -> List[Dict[str, Any]]:
        data = await self._t.request(
            "GET", f"/sandbox-templates/{template_id}/builds"
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def create_build(self, template_id: str, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            await self._t.request(
                "POST", f"/sandbox-templates/{template_id}/builds", json_body=body
            )
        )
