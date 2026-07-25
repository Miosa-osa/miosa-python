"""Product-aware template catalog.

This module is different from ``sandbox_templates``.
``sandbox_templates`` manages tenant-owned sandbox template build records.
``templates`` discovers product/template/size/readiness primitives across
sandboxes, computers, and appliances.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport
    from .sandbox_templates import AsyncSandboxTemplates, SandboxTemplates


def _catalog(data: Any) -> Dict[str, Any]:
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        data = data["data"]

    if not isinstance(data, dict):
        return {"templates": []}

    templates = data.get("templates")
    if not isinstance(templates, list):
        templates = []

    return {**data, "templates": templates}


class Templates:
    """Product-aware template discovery for sandbox, computer, and appliance."""

    def __init__(
        self,
        transport: "SyncTransport",
        *,
        sandbox_templates: Optional["SandboxTemplates"] = None,
    ) -> None:
        self._t = transport
        self._sandbox_templates = sandbox_templates

    def catalog(self) -> Dict[str, Any]:
        return _catalog(self._t.request("GET", "/templates"))

    def list(self, *, product: Optional[str] = None) -> List[Dict[str, Any]]:
        templates = self.catalog()["templates"]
        if product is None:
            return templates
        return [t for t in templates if t.get("product") == product]

    def get(self, template_id: str, *, product: Optional[str] = None) -> Dict[str, Any]:
        for template in self.list(product=product):
            if template.get("id") == template_id:
                return template
        raise KeyError(f"Template not found: {template_id}")

    def readiness(self, template_id: str, *, product: Optional[str] = None) -> List[Dict[str, Any]]:
        template = self.get(template_id, product=product)
        sizes = template.get("sizes")
        return sizes if isinstance(sizes, list) else []

    # Backward compatibility for older code that used client.templates for
    # tenant sandbox template CRUD. New code should use client.sandbox_templates.
    def create(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        if self._sandbox_templates is None:
            raise AttributeError("sandbox template CRUD is unavailable")
        return self._sandbox_templates.create(*args, **kwargs)

    def build_spec_schema(self) -> Dict[str, Any]:
        if self._sandbox_templates is None:
            raise AttributeError("sandbox template CRUD is unavailable")
        return self._sandbox_templates.build_spec_schema()

    def validate(self, build_spec: Dict[str, Any]) -> Dict[str, Any]:
        if self._sandbox_templates is None:
            raise AttributeError("sandbox template CRUD is unavailable")
        return self._sandbox_templates.validate(build_spec)

    def list_builds(self, template_id: str) -> List[Dict[str, Any]]:
        if self._sandbox_templates is None:
            raise AttributeError("sandbox template CRUD is unavailable")
        return self._sandbox_templates.list_builds(template_id)

    def create_build(self, template_id: str, **attrs: Any) -> Dict[str, Any]:
        if self._sandbox_templates is None:
            raise AttributeError("sandbox template CRUD is unavailable")
        return self._sandbox_templates.create_build(template_id, **attrs)


class AsyncTemplates:
    """Async product-aware template discovery."""

    def __init__(
        self,
        transport: "AsyncTransport",
        *,
        sandbox_templates: Optional["AsyncSandboxTemplates"] = None,
    ) -> None:
        self._t = transport
        self._sandbox_templates = sandbox_templates

    async def catalog(self) -> Dict[str, Any]:
        return _catalog(await self._t.request("GET", "/templates"))

    async def list(self, *, product: Optional[str] = None) -> List[Dict[str, Any]]:
        templates = (await self.catalog())["templates"]
        if product is None:
            return templates
        return [t for t in templates if t.get("product") == product]

    async def get(self, template_id: str, *, product: Optional[str] = None) -> Dict[str, Any]:
        for template in await self.list(product=product):
            if template.get("id") == template_id:
                return template
        raise KeyError(f"Template not found: {template_id}")

    async def readiness(
        self, template_id: str, *, product: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        template = await self.get(template_id, product=product)
        sizes = template.get("sizes")
        return sizes if isinstance(sizes, list) else []

    async def create(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        if self._sandbox_templates is None:
            raise AttributeError("sandbox template CRUD is unavailable")
        return await self._sandbox_templates.create(*args, **kwargs)

    async def build_spec_schema(self) -> Dict[str, Any]:
        if self._sandbox_templates is None:
            raise AttributeError("sandbox template CRUD is unavailable")
        return await self._sandbox_templates.build_spec_schema()

    async def validate(self, build_spec: Dict[str, Any]) -> Dict[str, Any]:
        if self._sandbox_templates is None:
            raise AttributeError("sandbox template CRUD is unavailable")
        return await self._sandbox_templates.validate(build_spec)

    async def list_builds(self, template_id: str) -> List[Dict[str, Any]]:
        if self._sandbox_templates is None:
            raise AttributeError("sandbox template CRUD is unavailable")
        return await self._sandbox_templates.list_builds(template_id)

    async def create_build(self, template_id: str, **attrs: Any) -> Dict[str, Any]:
        if self._sandbox_templates is None:
            raise AttributeError("sandbox template CRUD is unavailable")
        return await self._sandbox_templates.create_build(template_id, **attrs)
