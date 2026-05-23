"""Project integrations — third-party API key connections injected into VMs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(
    data: Any,
    keys: tuple[str, ...] = (
        "data",
        "project_integrations",
        "catalog",
        "items",
    ),
) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class ProjectIntegrations:
    """Per-project integrations (Stripe, Resend, Twilio, etc.).

    Credentials are encrypted at rest and injected as env vars into
    sandbox / deployment VMs at boot.
    """

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        """List project integrations."""
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request(
            "GET", "/project-integrations", params=params or None
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def catalog(self) -> List[Dict[str, Any]]:
        """List supported providers and their schemas."""
        data = self._t.request("GET", "/project-integrations/catalog")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def get(self, integration_id: str) -> Dict[str, Any]:
        """Get a project integration by id."""
        return _unwrap(
            self._t.request("GET", f"/project-integrations/{integration_id}")
        )

    def create(self, **attrs: Any) -> Dict[str, Any]:
        """Create a project integration."""
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            self._t.request("POST", "/project-integrations", json_body=body)
        )

    def update(self, integration_id: str, **attrs: Any) -> Dict[str, Any]:
        """Update a project integration."""
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            self._t.request(
                "PATCH",
                f"/project-integrations/{integration_id}",
                json_body=body,
            )
        )

    def delete(self, integration_id: str) -> None:
        """Delete a project integration."""
        self._t.request("DELETE", f"/project-integrations/{integration_id}")


class AsyncProjectIntegrations:
    """Async project integrations."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request(
            "GET", "/project-integrations", params=params or None
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def catalog(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", "/project-integrations/catalog")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def get(self, integration_id: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "GET", f"/project-integrations/{integration_id}"
            )
        )

    async def create(self, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            await self._t.request(
                "POST", "/project-integrations", json_body=body
            )
        )

    async def update(self, integration_id: str, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            await self._t.request(
                "PATCH",
                f"/project-integrations/{integration_id}",
                json_body=body,
            )
        )

    async def delete(self, integration_id: str) -> None:
        await self._t.request(
            "DELETE", f"/project-integrations/{integration_id}"
        )
