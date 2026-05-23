"""OpenComputers Apps resource — sync and async variants."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, List

from .types import AppCatalogEntry, AppInstall, AppInstallEvent

if TYPE_CHECKING:
    from ..._http import AsyncTransport, SyncTransport


def _parse_install_event(raw: dict) -> AppInstallEvent:
    data = raw.get("data", "")
    try:
        parsed = json.loads(data) if isinstance(data, str) and data else {}
    except (json.JSONDecodeError, ValueError):
        parsed = {"raw": data}
    return AppInstallEvent.model_validate(parsed)


class AppsResource:
    """App library management on remote hosts (sync)."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def catalog(self) -> List[AppCatalogEntry]:
        """List all available apps in the MIOSA app library."""
        result = self._transport.request("GET", "/opencomputers/apps")
        return [AppCatalogEntry.model_validate(item) for item in result.get("data", [])]

    def list_installed(self, host_id: str) -> List[AppInstall]:
        """List apps currently installed on a host."""
        result = self._transport.request("GET", f"/opencomputers/hosts/{host_id}/apps")
        return [AppInstall.model_validate(item) for item in result.get("data", [])]

    def install(self, host_id: str, app_id: str) -> AppInstall:
        """Install an app by catalog ID."""
        data = self._transport.request(
            "POST", f"/opencomputers/hosts/{host_id}/apps/{app_id}/install"
        )
        return AppInstall.model_validate(data)

    def get_install(self, host_id: str, install_id: str) -> AppInstall:
        """Get the current state of an install operation."""
        data = self._transport.request(
            "GET", f"/opencomputers/hosts/{host_id}/apps/installs/{install_id}"
        )
        return AppInstall.model_validate(data)

    def install_events(self, host_id: str, install_id: str) -> Iterator[AppInstallEvent]:
        """Stream install progress events."""
        for raw in self._transport.stream_sse(
            f"/opencomputers/hosts/{host_id}/apps/installs/{install_id}/events"
        ):
            yield _parse_install_event(raw)

    def uninstall(self, host_id: str, app_id: str) -> None:
        """Uninstall an app from a host."""
        self._transport.request("DELETE", f"/opencomputers/hosts/{host_id}/apps/{app_id}")

    def start_app(self, host_id: str, app_id: str) -> None:
        """Start a previously installed app."""
        self._transport.request("POST", f"/opencomputers/hosts/{host_id}/apps/{app_id}/start")


class AsyncAppsResource:
    """App library management on remote hosts (async)."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def catalog(self) -> List[AppCatalogEntry]:
        result = await self._transport.request("GET", "/opencomputers/apps")
        return [AppCatalogEntry.model_validate(item) for item in result.get("data", [])]

    async def list_installed(self, host_id: str) -> List[AppInstall]:
        result = await self._transport.request("GET", f"/opencomputers/hosts/{host_id}/apps")
        return [AppInstall.model_validate(item) for item in result.get("data", [])]

    async def install(self, host_id: str, app_id: str) -> AppInstall:
        data = await self._transport.request(
            "POST", f"/opencomputers/hosts/{host_id}/apps/{app_id}/install"
        )
        return AppInstall.model_validate(data)

    async def get_install(self, host_id: str, install_id: str) -> AppInstall:
        data = await self._transport.request(
            "GET", f"/opencomputers/hosts/{host_id}/apps/installs/{install_id}"
        )
        return AppInstall.model_validate(data)

    async def install_events(
        self, host_id: str, install_id: str
    ) -> AsyncIterator[AppInstallEvent]:
        async for raw in self._transport.stream_sse(
            f"/opencomputers/hosts/{host_id}/apps/installs/{install_id}/events"
        ):
            yield _parse_install_event(raw)

    async def uninstall(self, host_id: str, app_id: str) -> None:
        await self._transport.request(
            "DELETE", f"/opencomputers/hosts/{host_id}/apps/{app_id}"
        )

    async def start_app(self, host_id: str, app_id: str) -> None:
        await self._transport.request(
            "POST", f"/opencomputers/hosts/{host_id}/apps/{app_id}/start"
        )
