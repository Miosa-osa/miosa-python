"""Long-running service management for a computer.

Accessed via ``computer.services``. Wraps the platform's service-manager
endpoints — think systemd-lite for your VM.

Example::

    svc = computer.services.create(
        name="web",
        command="python -m http.server 8000",
        working_dir="/workspace",
        port=8000,
    )
    for log in computer.services.logs(svc.id):
        print(log.stream, log.line)
"""

from __future__ import annotations

import json as _json
from collections.abc import AsyncIterator, Iterator
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
)

from ..types import ServiceData, ServiceLogEvent

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, key: str = "data") -> Any:
    if isinstance(data, dict) and key in data and len(data) <= 2:
        return data[key]
    return data


def _parse_log(raw: dict) -> ServiceLogEvent:
    payload = raw.get("data", "")
    if isinstance(payload, str):
        try:
            parsed = _json.loads(payload)
        except (ValueError, TypeError):
            parsed = {"stream": "stdout", "line": payload}
    else:
        parsed = payload
    if not isinstance(parsed, dict):
        parsed = {"stream": "stdout", "line": str(parsed)}
    parsed.setdefault("stream", "stdout")
    parsed.setdefault("line", "")
    return ServiceLogEvent.model_validate(parsed)


def _build_create_body(
    *,
    name: str,
    command: str,
    working_dir: Optional[str],
    env: Optional[Dict[str, str]],
    restart_policy: Optional[str],
    port: Optional[int],
) -> dict:
    body: dict = {"name": name, "command": command}
    if working_dir is not None:
        body["working_dir"] = working_dir
    if env is not None:
        body["env"] = env
    if restart_policy is not None:
        body["restart_policy"] = restart_policy
    if port is not None:
        body["port"] = port
    return body


# ───────────────────────────────────────────────────────────────────────────
# Sync
# ───────────────────────────────────────────────────────────────────────────

class Services:
    """Synchronous service management scoped to a single computer."""

    def __init__(self, transport: SyncTransport, computer_id: str) -> None:
        self._transport = transport
        self._computer_id = computer_id

    def _base(self) -> str:
        return f"/computers/{self._computer_id}/services"

    def create(
        self,
        name: str,
        command: str,
        *,
        working_dir: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        restart_policy: Optional[str] = None,
        port: Optional[int] = None,
    ) -> ServiceData:
        """Register + start a new background service on the computer."""
        body = _build_create_body(
            name=name,
            command=command,
            working_dir=working_dir,
            env=env,
            restart_policy=restart_policy,
            port=port,
        )
        raw = self._transport.request("POST", self._base(), json_body=body)
        return ServiceData.model_validate(_unwrap(raw))

    def list(self) -> List[ServiceData]:
        """List all services on this computer."""
        raw = self._transport.request("GET", self._base())
        items = _unwrap(raw, "data") if isinstance(raw, dict) else raw
        if isinstance(items, dict) and "services" in items:
            items = items["services"]
        return [ServiceData.model_validate(s) for s in (items or [])]

    def get(self, service_id: str) -> ServiceData:
        """Fetch a single service by id."""
        raw = self._transport.request("GET", f"{self._base()}/{service_id}")
        return ServiceData.model_validate(_unwrap(raw))

    def start(self, service_id: str) -> ServiceData:
        """Start a stopped service."""
        raw = self._transport.request(
            "POST", f"{self._base()}/{service_id}/start"
        )
        return ServiceData.model_validate(_unwrap(raw))

    def stop(self, service_id: str) -> ServiceData:
        """Stop a running service (SIGTERM)."""
        raw = self._transport.request(
            "POST", f"{self._base()}/{service_id}/stop"
        )
        return ServiceData.model_validate(_unwrap(raw))

    def restart(self, service_id: str) -> ServiceData:
        """Restart a service — stop + start."""
        raw = self._transport.request(
            "POST", f"{self._base()}/{service_id}/restart"
        )
        return ServiceData.model_validate(_unwrap(raw))

    def delete(self, service_id: str) -> None:
        """Delete a service (stops it first if running)."""
        self._transport.request("DELETE", f"{self._base()}/{service_id}")

    def logs(
        self,
        service_id: str,
        *,
        follow: bool = True,
    ) -> Iterator[ServiceLogEvent]:
        """Iterate log lines for a service via SSE.

        Set ``follow=False`` to only replay existing logs and return.
        """
        path = f"{self._base()}/{service_id}/logs"
        params = {"follow": "true" if follow else "false"}
        for raw in self._transport.stream_sse(path, params=params):
            yield _parse_log(raw)


# ───────────────────────────────────────────────────────────────────────────
# Async
# ───────────────────────────────────────────────────────────────────────────

class AsyncServices:
    """Asynchronous service management."""

    def __init__(self, transport: AsyncTransport, computer_id: str) -> None:
        self._transport = transport
        self._computer_id = computer_id

    def _base(self) -> str:
        return f"/computers/{self._computer_id}/services"

    async def create(
        self,
        name: str,
        command: str,
        *,
        working_dir: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        restart_policy: Optional[str] = None,
        port: Optional[int] = None,
    ) -> ServiceData:
        body = _build_create_body(
            name=name,
            command=command,
            working_dir=working_dir,
            env=env,
            restart_policy=restart_policy,
            port=port,
        )
        raw = await self._transport.request("POST", self._base(), json_body=body)
        return ServiceData.model_validate(_unwrap(raw))

    async def list(self) -> List[ServiceData]:
        raw = await self._transport.request("GET", self._base())
        items = _unwrap(raw, "data") if isinstance(raw, dict) else raw
        if isinstance(items, dict) and "services" in items:
            items = items["services"]
        return [ServiceData.model_validate(s) for s in (items or [])]

    async def get(self, service_id: str) -> ServiceData:
        raw = await self._transport.request(
            "GET", f"{self._base()}/{service_id}"
        )
        return ServiceData.model_validate(_unwrap(raw))

    async def start(self, service_id: str) -> ServiceData:
        raw = await self._transport.request(
            "POST", f"{self._base()}/{service_id}/start"
        )
        return ServiceData.model_validate(_unwrap(raw))

    async def stop(self, service_id: str) -> ServiceData:
        raw = await self._transport.request(
            "POST", f"{self._base()}/{service_id}/stop"
        )
        return ServiceData.model_validate(_unwrap(raw))

    async def restart(self, service_id: str) -> ServiceData:
        raw = await self._transport.request(
            "POST", f"{self._base()}/{service_id}/restart"
        )
        return ServiceData.model_validate(_unwrap(raw))

    async def delete(self, service_id: str) -> None:
        await self._transport.request(
            "DELETE", f"{self._base()}/{service_id}"
        )

    async def logs(
        self,
        service_id: str,
        *,
        follow: bool = True,
    ) -> AsyncIterator[ServiceLogEvent]:
        path = f"{self._base()}/{service_id}/logs"
        params = {"follow": "true" if follow else "false"}
        async for raw in self._transport.stream_sse(path, params=params):
            yield _parse_log(raw)
