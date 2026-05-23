"""Extra sub-resources attached to :class:`Computer` for deep platform coverage.

Each sub-resource wraps a discrete cluster of backend routes that all live
under ``/computers/:id/...``. They follow the same construction pattern as
:class:`~miosa.resources.checkpoints.Checkpoints` and friends: instantiate
with ``(transport, computer_id)``.

Sub-resources defined here:

* :class:`ComputerTerminal`  — POST ``/terminal``, POST ``/pty/:sid/resize``
* :class:`ComputerOsa`       — POST/DELETE/GET ``/osa/*``
* :class:`ComputerAutoStop`  — GET/PATCH ``/auto-stop``
* :class:`ComputerInbox`     — GET/PATCH ``/inbox``
* :class:`ComputerEnv`       — GET/POST/PATCH/DELETE ``/env``
* :class:`ComputerLogs`      — GET ``/logs`` + GET ``/logs/stream`` (SSE)
* :class:`ComputerMetrics`   — GET ``/metrics``
* :class:`ComputerPorts`     — GET/POST/PATCH/DELETE ``/ports``
* :class:`ComputerVolumes`   — GET/POST/DELETE ``/volumes``

Both sync and async variants are provided.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data",)) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data and len(data) <= 2:
                return data[k]
    return data


def _list_unwrap(data: Any, keys: tuple[str, ...]) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in keys:
            v = data.get(k)
            if isinstance(v, list):
                return v
    return []


# ───────────────────────────────────────────────────────────────────────────
# Terminal
# ───────────────────────────────────────────────────────────────────────────

class ComputerTerminal:
    """PTY session management for a Computer.

    Maps to ``POST /computers/:id/terminal`` and
    ``POST /computers/:id/pty/:session_id/resize``.
    """

    def __init__(self, transport: SyncTransport, computer_id: str) -> None:
        self._t = transport
        self._cid = computer_id

    def create(
        self,
        *,
        cols: Optional[int] = None,
        rows: Optional[int] = None,
        shell: Optional[str] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Open a new PTY session. Returns the server payload (session id, etc.)."""
        body = {
            k: v for k, v in {
                "cols": cols,
                "rows": rows,
                "shell": shell,
                "cwd": cwd,
                "env": env,
            }.items() if v is not None
        }
        raw = self._t.request("POST", f"/computers/{self._cid}/terminal", json_body=body)
        return _unwrap(raw)

    def resize(self, session_id: str, cols: int, rows: int) -> Dict[str, Any]:
        """Resize an existing PTY session."""
        raw = self._t.request(
            "POST",
            f"/computers/{self._cid}/pty/{session_id}/resize",
            json_body={"cols": cols, "rows": rows},
        )
        return _unwrap(raw)


class AsyncComputerTerminal:
    """Async PTY session management."""

    def __init__(self, transport: AsyncTransport, computer_id: str) -> None:
        self._t = transport
        self._cid = computer_id

    async def create(
        self,
        *,
        cols: Optional[int] = None,
        rows: Optional[int] = None,
        shell: Optional[str] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        body = {
            k: v for k, v in {
                "cols": cols,
                "rows": rows,
                "shell": shell,
                "cwd": cwd,
                "env": env,
            }.items() if v is not None
        }
        raw = await self._t.request("POST", f"/computers/{self._cid}/terminal", json_body=body)
        return _unwrap(raw)

    async def resize(self, session_id: str, cols: int, rows: int) -> Dict[str, Any]:
        raw = await self._t.request(
            "POST",
            f"/computers/{self._cid}/pty/{session_id}/resize",
            json_body={"cols": cols, "rows": rows},
        )
        return _unwrap(raw)


# ───────────────────────────────────────────────────────────────────────────
# OSA (in-VM agent dispatch)
# ───────────────────────────────────────────────────────────────────────────

class ComputerOsa:
    """Task dispatch to the in-VM OSA agent.

    Wraps:
      * POST   /computers/:id/osa/task
      * DELETE /computers/:id/osa/task
      * GET    /computers/:id/osa/status
      * POST   /computers/:id/osa/configure
    """

    def __init__(self, transport: SyncTransport, computer_id: str) -> None:
        self._t = transport
        self._cid = computer_id

    def submit_task(self, task: str, **params: Any) -> Dict[str, Any]:
        """Submit a free-form task to the in-VM OSA agent."""
        body = {"task": task, **{k: v for k, v in params.items() if v is not None}}
        raw = self._t.request("POST", f"/computers/{self._cid}/osa/task", json_body=body)
        return _unwrap(raw)

    def cancel_task(self) -> Dict[str, Any]:
        """Cancel the currently-running OSA task, if any."""
        raw = self._t.request("DELETE", f"/computers/{self._cid}/osa/task")
        return _unwrap(raw)

    def status(self) -> Dict[str, Any]:
        """Return OSA's current task / configuration / health snapshot."""
        raw = self._t.request("GET", f"/computers/{self._cid}/osa/status")
        return _unwrap(raw)

    def configure(self, **config: Any) -> Dict[str, Any]:
        """Update OSA runtime configuration (model, tools, secrets, etc.)."""
        body = {k: v for k, v in config.items() if v is not None}
        raw = self._t.request("POST", f"/computers/{self._cid}/osa/configure", json_body=body)
        return _unwrap(raw)


class AsyncComputerOsa:
    """Async in-VM OSA agent control."""

    def __init__(self, transport: AsyncTransport, computer_id: str) -> None:
        self._t = transport
        self._cid = computer_id

    async def submit_task(self, task: str, **params: Any) -> Dict[str, Any]:
        body = {"task": task, **{k: v for k, v in params.items() if v is not None}}
        raw = await self._t.request("POST", f"/computers/{self._cid}/osa/task", json_body=body)
        return _unwrap(raw)

    async def cancel_task(self) -> Dict[str, Any]:
        raw = await self._t.request("DELETE", f"/computers/{self._cid}/osa/task")
        return _unwrap(raw)

    async def status(self) -> Dict[str, Any]:
        raw = await self._t.request("GET", f"/computers/{self._cid}/osa/status")
        return _unwrap(raw)

    async def configure(self, **config: Any) -> Dict[str, Any]:
        body = {k: v for k, v in config.items() if v is not None}
        raw = await self._t.request("POST", f"/computers/{self._cid}/osa/configure", json_body=body)
        return _unwrap(raw)


# ───────────────────────────────────────────────────────────────────────────
# Auto-stop
# ───────────────────────────────────────────────────────────────────────────

class ComputerAutoStop:
    """Read/update idle-timeout config (GET/PATCH ``/auto-stop``)."""

    def __init__(self, transport: SyncTransport, computer_id: str) -> None:
        self._t = transport
        self._cid = computer_id

    def get(self) -> Dict[str, Any]:
        """Return the current auto-stop configuration."""
        raw = self._t.request("GET", f"/computers/{self._cid}/auto-stop")
        return _unwrap(raw)

    def update(self, seconds: int) -> Dict[str, Any]:
        """Set the idle timeout in seconds (0 disables auto-stop)."""
        raw = self._t.request(
            "PATCH",
            f"/computers/{self._cid}/auto-stop",
            json_body={"seconds": seconds},
        )
        return _unwrap(raw)


class AsyncComputerAutoStop:
    """Async auto-stop control."""

    def __init__(self, transport: AsyncTransport, computer_id: str) -> None:
        self._t = transport
        self._cid = computer_id

    async def get(self) -> Dict[str, Any]:
        raw = await self._t.request("GET", f"/computers/{self._cid}/auto-stop")
        return _unwrap(raw)

    async def update(self, seconds: int) -> Dict[str, Any]:
        raw = await self._t.request(
            "PATCH",
            f"/computers/{self._cid}/auto-stop",
            json_body={"seconds": seconds},
        )
        return _unwrap(raw)


# ───────────────────────────────────────────────────────────────────────────
# Inbox (inbound-email inbox for Optimal)
# ───────────────────────────────────────────────────────────────────────────

class ComputerInbox:
    """Per-computer inbox config (GET/PATCH ``/inbox``)."""

    def __init__(self, transport: SyncTransport, computer_id: str) -> None:
        self._t = transport
        self._cid = computer_id

    def get(self) -> Dict[str, Any]:
        """Fetch the current inbox configuration."""
        raw = self._t.request("GET", f"/computers/{self._cid}/inbox")
        return _unwrap(raw)

    def update(self, **fields: Any) -> Dict[str, Any]:
        """Patch one or more inbox fields (e.g. ``alias``, ``enabled``)."""
        body = {k: v for k, v in fields.items() if v is not None}
        raw = self._t.request("PATCH", f"/computers/{self._cid}/inbox", json_body=body)
        return _unwrap(raw)


class AsyncComputerInbox:
    """Async per-computer inbox control."""

    def __init__(self, transport: AsyncTransport, computer_id: str) -> None:
        self._t = transport
        self._cid = computer_id

    async def get(self) -> Dict[str, Any]:
        raw = await self._t.request("GET", f"/computers/{self._cid}/inbox")
        return _unwrap(raw)

    async def update(self, **fields: Any) -> Dict[str, Any]:
        body = {k: v for k, v in fields.items() if v is not None}
        raw = await self._t.request("PATCH", f"/computers/{self._cid}/inbox", json_body=body)
        return _unwrap(raw)


# ───────────────────────────────────────────────────────────────────────────
# Env vars
# ───────────────────────────────────────────────────────────────────────────

class ComputerEnv:
    """Encrypted env var CRUD scoped to one Computer.

    * GET    /computers/:id/env             → list
    * POST   /computers/:id/env             → create (single)
    * PATCH  /computers/:id/env/:name       → update value
    * DELETE /computers/:id/env/:name       → remove

    ``bulk_set`` falls back to N individual POSTs (the backend has no
    bulk endpoint yet).
    """

    def __init__(self, transport: SyncTransport, computer_id: str) -> None:
        self._t = transport
        self._cid = computer_id

    def _base(self) -> str:
        return f"/computers/{self._cid}/env"

    def list(self) -> List[Dict[str, Any]]:
        """List all env vars (values may be masked depending on server policy)."""
        raw = self._t.request("GET", self._base())
        return _list_unwrap(raw, ("data", "env", "items"))

    def set(self, name: str, value: str) -> Dict[str, Any]:
        """Create a new env var. Use :meth:`update` to change an existing one."""
        raw = self._t.request(
            "POST",
            self._base(),
            json_body={"name": name, "value": value},
        )
        return _unwrap(raw)

    def update(self, name: str, value: str) -> Dict[str, Any]:
        """Patch the value of an existing env var by name."""
        raw = self._t.request(
            "PATCH",
            f"{self._base()}/{name}",
            json_body={"value": value},
        )
        return _unwrap(raw)

    def delete(self, name: str) -> None:
        """Remove an env var by name."""
        self._t.request("DELETE", f"{self._base()}/{name}")

    def bulk_set(self, env: Dict[str, str]) -> List[Dict[str, Any]]:
        """Convenience: create one env var per entry in ``env``."""
        return [self.set(name, value) for name, value in env.items()]


class AsyncComputerEnv:
    """Async env var CRUD."""

    def __init__(self, transport: AsyncTransport, computer_id: str) -> None:
        self._t = transport
        self._cid = computer_id

    def _base(self) -> str:
        return f"/computers/{self._cid}/env"

    async def list(self) -> List[Dict[str, Any]]:
        raw = await self._t.request("GET", self._base())
        return _list_unwrap(raw, ("data", "env", "items"))

    async def set(self, name: str, value: str) -> Dict[str, Any]:
        raw = await self._t.request(
            "POST",
            self._base(),
            json_body={"name": name, "value": value},
        )
        return _unwrap(raw)

    async def update(self, name: str, value: str) -> Dict[str, Any]:
        raw = await self._t.request(
            "PATCH",
            f"{self._base()}/{name}",
            json_body={"value": value},
        )
        return _unwrap(raw)

    async def delete(self, name: str) -> None:
        await self._t.request("DELETE", f"{self._base()}/{name}")

    async def bulk_set(self, env: Dict[str, str]) -> List[Dict[str, Any]]:
        return [await self.set(name, value) for name, value in env.items()]


# ───────────────────────────────────────────────────────────────────────────
# Logs
# ───────────────────────────────────────────────────────────────────────────

class ComputerLogs:
    """Read + stream VM logs.

    * GET /computers/:id/logs         — JSON snapshot (last N lines)
    * GET /computers/:id/logs/stream  — text/event-stream of new lines
    """

    def __init__(self, transport: SyncTransport, computer_id: str) -> None:
        self._t = transport
        self._cid = computer_id

    def get(
        self,
        *,
        lines: Optional[int] = None,
        since: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch the most recent log snapshot."""
        params = {k: v for k, v in {"lines": lines, "since": since}.items() if v is not None}
        raw = self._t.request("GET", f"/computers/{self._cid}/logs", params=params or None)
        return _unwrap(raw)

    def stream(self) -> Iterator[Dict[str, Any]]:
        """Stream live log events as SSE dicts ``{type, data, id}``."""
        yield from self._t.stream_sse(f"/computers/{self._cid}/logs/stream")


class AsyncComputerLogs:
    """Async log read + stream."""

    def __init__(self, transport: AsyncTransport, computer_id: str) -> None:
        self._t = transport
        self._cid = computer_id

    async def get(
        self,
        *,
        lines: Optional[int] = None,
        since: Optional[str] = None,
    ) -> Dict[str, Any]:
        params = {k: v for k, v in {"lines": lines, "since": since}.items() if v is not None}
        raw = await self._t.request("GET", f"/computers/{self._cid}/logs", params=params or None)
        return _unwrap(raw)

    async def stream(self) -> AsyncIterator[Dict[str, Any]]:
        async for event in self._t.stream_sse(f"/computers/{self._cid}/logs/stream"):
            yield event


# ───────────────────────────────────────────────────────────────────────────
# Metrics
# ───────────────────────────────────────────────────────────────────────────

class ComputerMetrics:
    """Read time-series RAM/CPU/credit metrics."""

    def __init__(self, transport: SyncTransport, computer_id: str) -> None:
        self._t = transport
        self._cid = computer_id

    def get(self, window: str = "1h") -> Dict[str, Any]:
        """Return metric series for ``window`` (e.g. ``"1h"``, ``"24h"``, ``"7d"``)."""
        raw = self._t.request(
            "GET",
            f"/computers/{self._cid}/metrics",
            params={"window": window},
        )
        return _unwrap(raw)


class AsyncComputerMetrics:
    """Async metrics reader."""

    def __init__(self, transport: AsyncTransport, computer_id: str) -> None:
        self._t = transport
        self._cid = computer_id

    async def get(self, window: str = "1h") -> Dict[str, Any]:
        raw = await self._t.request(
            "GET",
            f"/computers/{self._cid}/metrics",
            params={"window": window},
        )
        return _unwrap(raw)


# ───────────────────────────────────────────────────────────────────────────
# Ports
# ───────────────────────────────────────────────────────────────────────────

class ComputerPorts:
    """Per-port visibility control.

    * GET    /computers/:id/ports          — list
    * POST   /computers/:id/ports          — create
    * PATCH  /computers/:id/ports/:port    — update
    * DELETE /computers/:id/ports/:port    — delete

    The backend does not expose a single-port GET; :meth:`get` filters
    the list response client-side for ergonomics.
    """

    def __init__(self, transport: SyncTransport, computer_id: str) -> None:
        self._t = transport
        self._cid = computer_id

    def _base(self) -> str:
        return f"/computers/{self._cid}/ports"

    def list(self) -> List[Dict[str, Any]]:
        raw = self._t.request("GET", self._base())
        return _list_unwrap(raw, ("data", "ports", "items"))

    def get(self, port: int) -> Optional[Dict[str, Any]]:
        """Return the port record for ``port``, or ``None`` if not exposed."""
        for record in self.list():
            if int(record.get("port", -1)) == int(port):
                return record
        return None

    def create(self, port: int, **opts: Any) -> Dict[str, Any]:
        """Expose ``port`` with the given visibility options."""
        body = {"port": port, **{k: v for k, v in opts.items() if v is not None}}
        raw = self._t.request("POST", self._base(), json_body=body)
        return _unwrap(raw)

    def update(self, port: int, **opts: Any) -> Dict[str, Any]:
        """Patch visibility / auth options for ``port``."""
        body = {k: v for k, v in opts.items() if v is not None}
        raw = self._t.request("PATCH", f"{self._base()}/{port}", json_body=body)
        return _unwrap(raw)

    def delete(self, port: int) -> None:
        """Stop exposing ``port``."""
        self._t.request("DELETE", f"{self._base()}/{port}")


class AsyncComputerPorts:
    """Async per-port visibility control."""

    def __init__(self, transport: AsyncTransport, computer_id: str) -> None:
        self._t = transport
        self._cid = computer_id

    def _base(self) -> str:
        return f"/computers/{self._cid}/ports"

    async def list(self) -> List[Dict[str, Any]]:
        raw = await self._t.request("GET", self._base())
        return _list_unwrap(raw, ("data", "ports", "items"))

    async def get(self, port: int) -> Optional[Dict[str, Any]]:
        for record in await self.list():
            if int(record.get("port", -1)) == int(port):
                return record
        return None

    async def create(self, port: int, **opts: Any) -> Dict[str, Any]:
        body = {"port": port, **{k: v for k, v in opts.items() if v is not None}}
        raw = await self._t.request("POST", self._base(), json_body=body)
        return _unwrap(raw)

    async def update(self, port: int, **opts: Any) -> Dict[str, Any]:
        body = {k: v for k, v in opts.items() if v is not None}
        raw = await self._t.request("PATCH", f"{self._base()}/{port}", json_body=body)
        return _unwrap(raw)

    async def delete(self, port: int) -> None:
        await self._t.request("DELETE", f"{self._base()}/{port}")


# ───────────────────────────────────────────────────────────────────────────
# Volume attachments (per-computer)
# ───────────────────────────────────────────────────────────────────────────

class ComputerVolumes:
    """Per-computer volume attachment.

    * GET    /computers/:id/volumes          — list attachments
    * POST   /computers/:id/volumes          — attach a volume
    * DELETE /computers/:id/volumes/:aid     — detach an attachment
    """

    def __init__(self, transport: SyncTransport, computer_id: str) -> None:
        self._t = transport
        self._cid = computer_id

    def _base(self) -> str:
        return f"/computers/{self._cid}/volumes"

    def list(self) -> List[Dict[str, Any]]:
        raw = self._t.request("GET", self._base())
        return _list_unwrap(raw, ("data", "attachments", "volumes", "items"))

    def attach(self, volume_id: str, mount_path: str) -> Dict[str, Any]:
        """Attach ``volume_id`` at ``mount_path`` inside the VM."""
        raw = self._t.request(
            "POST",
            self._base(),
            json_body={"volume_id": volume_id, "mount_path": mount_path},
        )
        return _unwrap(raw)

    def detach(self, attachment_id: str) -> None:
        """Detach an existing attachment by attachment id."""
        self._t.request("DELETE", f"{self._base()}/{attachment_id}")


class AsyncComputerVolumes:
    """Async per-computer volume attachment."""

    def __init__(self, transport: AsyncTransport, computer_id: str) -> None:
        self._t = transport
        self._cid = computer_id

    def _base(self) -> str:
        return f"/computers/{self._cid}/volumes"

    async def list(self) -> List[Dict[str, Any]]:
        raw = await self._t.request("GET", self._base())
        return _list_unwrap(raw, ("data", "attachments", "volumes", "items"))

    async def attach(self, volume_id: str, mount_path: str) -> Dict[str, Any]:
        raw = await self._t.request(
            "POST",
            self._base(),
            json_body={"volume_id": volume_id, "mount_path": mount_path},
        )
        return _unwrap(raw)

    async def detach(self, attachment_id: str) -> None:
        await self._t.request("DELETE", f"{self._base()}/{attachment_id}")


__all__ = [
    "AsyncComputerAutoStop",
    "AsyncComputerEnv",
    "AsyncComputerInbox",
    "AsyncComputerLogs",
    "AsyncComputerMetrics",
    "AsyncComputerOsa",
    "AsyncComputerPorts",
    "AsyncComputerTerminal",
    "AsyncComputerVolumes",
    "ComputerAutoStop",
    "ComputerEnv",
    "ComputerInbox",
    "ComputerLogs",
    "ComputerMetrics",
    "ComputerOsa",
    "ComputerPorts",
    "ComputerTerminal",
    "ComputerVolumes",
]
