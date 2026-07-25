"""Unified devices — sandbox workers and desktop computers behind one API."""

from __future__ import annotations

import builtins
import json
import shlex
from typing import TYPE_CHECKING, Any, Callable, Union
from urllib.parse import quote

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data",)) -> Any:
    if isinstance(data, dict):
        for key in keys:
            if key in data:
                return data[key]
    return data


def _unwrap_list(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "devices", "items", "entries"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    return []


def _compact(body: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in body.items() if value is not None}


def _device_path(device_id: str) -> str:
    return quote(device_id, safe="")


def _list_params(**filters: Any) -> dict[str, Any]:
    return _compact(
        {
            "kind": filters.get("kind") or filters.get("type"),
            "workspace_id": filters.get("workspace_id") or filters.get("workspaceId"),
            "project_id": filters.get("project_id") or filters.get("projectId"),
        }
    )


def _exec_body(command: str | list[str], **params: Any) -> dict[str, Any]:
    return _compact(
        {
            "command": command,
            "timeout_ms": params.get("timeout_ms") or params.get("timeoutMs"),
            "cwd": params.get("cwd"),
            "env": params.get("env"),
        }
    )


def _file_params(path: str | None = None) -> dict[str, Any]:
    return _compact({"path": path})


def _write_body(path: str, **params: Any) -> dict[str, Any]:
    return _compact(
        {
            "path": path,
            "content": params.get("content"),
            "content_base64": params.get("content_base64")
            or params.get("contentBase64"),
        }
    )


RUNTIME_BINARIES: dict[str, list[str]] = {
    "claude-code": ["claude-code", "claude"],
    "claude": ["claude"],
    "codex": ["codex"],
    "hermes": ["hermes"],
    "osa": ["osa"],
    "pi": ["pi"],
    "custom": [],
}

ConnectorBinding = Union[str, dict[str, Any]]


def _runtime_probe_command(runtime: str) -> str:
    binaries = RUNTIME_BINARIES.get(runtime, [])
    if not binaries:
        return "printf 'custom runtime manifest written\\n'"
    checks = " || ".join(
        f"command -v {shlex.quote(binary)} >/dev/null 2>&1" for binary in binaries
    )
    display = " or ".join(binaries)
    return (
        f"{checks} && printf 'runtime available: {display}\\n' || "
        f"{{ printf 'runtime missing: {display}\\n' >&2; exit 127; }}"
    )


def _manifest_path(cwd: str) -> str:
    return f"{cwd.rstrip('/')}/.miosa/runtime-bootstrap.json"


class Devices:
    """Unified device API for sandbox workers and desktop computers."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def list(self, **filters: Any) -> builtins.list[dict[str, Any]]:
        """List devices visible to the current tenant/workspace."""
        data = self._t.request("GET", "/devices", params=_list_params(**filters) or None)
        return _unwrap_list(data)

    def get(self, device_id: str) -> dict[str, Any]:
        """Show one device by id."""
        return _unwrap(self._t.request("GET", f"/devices/{_device_path(device_id)}"))

    show = get

    def capabilities(self, device_id: str) -> dict[str, Any]:
        """Return operations supported by this device."""
        return _unwrap(
            self._t.request("GET", f"/devices/{_device_path(device_id)}/capabilities")
        )

    def exec(
        self,
        device_id: str,
        command: str | builtins.list[str],
        **params: Any,
    ) -> dict[str, Any]:
        """Run a command inside the device."""
        return _unwrap(
            self._t.request(
                "POST",
                f"/devices/{_device_path(device_id)}/exec",
                json_body=_exec_body(command, **params),
            )
        )

    def list_files(self, device_id: str, path: str | None = None) -> builtins.list[dict[str, Any]]:
        """List files inside the device filesystem."""
        data = self._t.request(
            "GET",
            f"/devices/{_device_path(device_id)}/files",
            params=_file_params(path) or None,
        )
        return _unwrap_list(data)

    def read_file(self, device_id: str, path: str) -> dict[str, Any]:
        """Read a file. Content is returned base64-encoded by the API."""
        return _unwrap(
            self._t.request(
                "GET",
                f"/devices/{_device_path(device_id)}/files/read",
                params=_file_params(path),
            )
        )

    def write_file(self, device_id: str, path: str, **params: Any) -> dict[str, Any]:
        """Write text or base64 content into the device filesystem."""
        return _unwrap(
            self._t.request(
                "POST",
                f"/devices/{_device_path(device_id)}/files/write",
                json_body=_write_body(path, **params),
            )
        )

    def expose(self, device_id: str, port: int) -> dict[str, Any]:
        """Expose a device port through MIOSA routing."""
        return _unwrap(
            self._t.request(
                "POST",
                f"/devices/{_device_path(device_id)}/expose",
                json_body={"port": port},
            )
        )

    def browser(self, device_id: str) -> dict[str, Any]:
        """Return browser/desktop connection details for a computer-backed device."""
        return _unwrap(
            self._t.request("GET", f"/devices/{_device_path(device_id)}/browser")
        )

    def pause(self, device_id: str) -> dict[str, Any]:
        """Pause a device session when supported."""
        return _unwrap(
            self._t.request("POST", f"/devices/{_device_path(device_id)}/pause", json_body={})
        )

    def stop(self, device_id: str) -> dict[str, Any]:
        """Stop a device session when supported."""
        return _unwrap(
            self._t.request("POST", f"/devices/{_device_path(device_id)}/stop", json_body={})
        )

    def resume(self, device_id: str) -> dict[str, Any]:
        """Resume a device session when supported."""
        return _unwrap(
            self._t.request("POST", f"/devices/{_device_path(device_id)}/resume", json_body={})
        )

    def extend(self, device_id: str, timeout_sec: int) -> dict[str, Any]:
        """Extend a device session timeout when supported."""
        return _unwrap(
            self._t.request(
                "POST",
                f"/devices/{_device_path(device_id)}/extend",
                json_body={"timeout_sec": timeout_sec},
            )
        )

    def destroy(self, device_id: str) -> dict[str, Any]:
        """Destroy/delete a device when supported."""
        return _unwrap(
            self._t.request("DELETE", f"/devices/{_device_path(device_id)}")
        )

    def bootstrap(
        self,
        device_id: str,
        *,
        runtime: str,
        cwd: str = "/workspace",
        connectors: builtins.list[ConnectorBinding] | None = None,
        env: dict[str, str] | None = None,
        mcp: builtins.list[dict[str, str]] | None = None,
        install_command: str | None = None,
        skip_probe: bool = False,
    ) -> dict[str, Any]:
        """Write a runtime bootstrap manifest and optionally install/probe."""
        normalized = runtime.strip().lower()
        manifest_path = _manifest_path(cwd)
        steps: list[dict[str, Any]] = []
        manifest = {
            "version": 1,
            "runtime": normalized,
            "cwd": cwd,
            "expected_binaries": RUNTIME_BINARIES.get(normalized, []),
            "connectors": connectors or [],
            "env": env or {},
            "mcp": mcp or [],
            "created_by": "miosa-python",
        }

        self._record_step(
            steps,
            "write_manifest",
            lambda: self.write_file(
                device_id,
                manifest_path,
                content=json.dumps(manifest, indent=2) + "\n",
            ),
        )

        if install_command:
            self._record_step(
                steps,
                "install",
                lambda: self.exec(
                    device_id,
                    install_command,
                    cwd=cwd,
                    timeout_ms=600_000,
                ),
            )

        if not skip_probe:
            self._record_step(
                steps,
                "probe",
                lambda: self.exec(
                    device_id,
                    _runtime_probe_command(normalized),
                    cwd=cwd,
                    timeout_ms=60_000,
                ),
            )

        return {
            "device_id": device_id,
            "ok": all(step["ok"] for step in steps),
            "runtime": normalized,
            "manifest_path": manifest_path,
            "steps": steps,
        }

    def _record_step(
        self,
        steps: builtins.list[dict[str, Any]],
        name: str,
        fn: Callable[[], Any],
    ) -> None:
        try:
            steps.append({"name": name, "ok": True, "detail": fn()})
        except Exception as exc:  # pragma: no cover - exercised through API errors
            steps.append({"name": name, "ok": False, "error": str(exc)})


class AsyncDevices:
    """Async unified device API."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def list(self, **filters: Any) -> builtins.list[dict[str, Any]]:
        data = await self._t.request(
            "GET", "/devices", params=_list_params(**filters) or None
        )
        return _unwrap_list(data)

    async def get(self, device_id: str) -> dict[str, Any]:
        return _unwrap(
            await self._t.request("GET", f"/devices/{_device_path(device_id)}")
        )

    show = get

    async def capabilities(self, device_id: str) -> dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "GET", f"/devices/{_device_path(device_id)}/capabilities"
            )
        )

    async def exec(
        self,
        device_id: str,
        command: str | builtins.list[str],
        **params: Any,
    ) -> dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                f"/devices/{_device_path(device_id)}/exec",
                json_body=_exec_body(command, **params),
            )
        )

    async def list_files(
        self, device_id: str, path: str | None = None
    ) -> builtins.list[dict[str, Any]]:
        data = await self._t.request(
            "GET",
            f"/devices/{_device_path(device_id)}/files",
            params=_file_params(path) or None,
        )
        return _unwrap_list(data)

    async def read_file(self, device_id: str, path: str) -> dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "GET",
                f"/devices/{_device_path(device_id)}/files/read",
                params=_file_params(path),
            )
        )

    async def write_file(self, device_id: str, path: str, **params: Any) -> dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                f"/devices/{_device_path(device_id)}/files/write",
                json_body=_write_body(path, **params),
            )
        )

    async def expose(self, device_id: str, port: int) -> dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                f"/devices/{_device_path(device_id)}/expose",
                json_body={"port": port},
            )
        )

    async def browser(self, device_id: str) -> dict[str, Any]:
        return _unwrap(
            await self._t.request("GET", f"/devices/{_device_path(device_id)}/browser")
        )

    async def pause(self, device_id: str) -> dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST", f"/devices/{_device_path(device_id)}/pause", json_body={}
            )
        )

    async def stop(self, device_id: str) -> dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST", f"/devices/{_device_path(device_id)}/stop", json_body={}
            )
        )

    async def resume(self, device_id: str) -> dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST", f"/devices/{_device_path(device_id)}/resume", json_body={}
            )
        )

    async def extend(self, device_id: str, timeout_sec: int) -> dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                f"/devices/{_device_path(device_id)}/extend",
                json_body={"timeout_sec": timeout_sec},
            )
        )

    async def destroy(self, device_id: str) -> dict[str, Any]:
        return _unwrap(
            await self._t.request("DELETE", f"/devices/{_device_path(device_id)}")
        )

    async def bootstrap(
        self,
        device_id: str,
        *,
        runtime: str,
        cwd: str = "/workspace",
        connectors: builtins.list[ConnectorBinding] | None = None,
        env: dict[str, str] | None = None,
        mcp: builtins.list[dict[str, str]] | None = None,
        install_command: str | None = None,
        skip_probe: bool = False,
    ) -> dict[str, Any]:
        normalized = runtime.strip().lower()
        manifest_path = _manifest_path(cwd)
        steps: list[dict[str, Any]] = []
        manifest = {
            "version": 1,
            "runtime": normalized,
            "cwd": cwd,
            "expected_binaries": RUNTIME_BINARIES.get(normalized, []),
            "connectors": connectors or [],
            "env": env or {},
            "mcp": mcp or [],
            "created_by": "miosa-python",
        }

        await self._record_step(
            steps,
            "write_manifest",
            lambda: self.write_file(
                device_id,
                manifest_path,
                content=json.dumps(manifest, indent=2) + "\n",
            ),
        )

        if install_command:
            await self._record_step(
                steps,
                "install",
                lambda: self.exec(
                    device_id,
                    install_command,
                    cwd=cwd,
                    timeout_ms=600_000,
                ),
            )

        if not skip_probe:
            await self._record_step(
                steps,
                "probe",
                lambda: self.exec(
                    device_id,
                    _runtime_probe_command(normalized),
                    cwd=cwd,
                    timeout_ms=60_000,
                ),
            )

        return {
            "device_id": device_id,
            "ok": all(step["ok"] for step in steps),
            "runtime": normalized,
            "manifest_path": manifest_path,
            "steps": steps,
        }

    async def _record_step(
        self,
        steps: builtins.list[dict[str, Any]],
        name: str,
        fn: Callable[[], Any],
    ) -> None:
        try:
            steps.append({"name": name, "ok": True, "detail": await fn()})
        except Exception as exc:  # pragma: no cover - exercised through API errors
            steps.append({"name": name, "ok": False, "error": str(exc)})
