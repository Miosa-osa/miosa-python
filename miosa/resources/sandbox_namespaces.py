"""Small namespace helpers for bound sandbox handles."""

from __future__ import annotations

import base64
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .sandboxes import AsyncSandbox, ExecOptions, ExecResult, Sandbox, SandboxEvent


# ─── Background process result types ────────────────────────────────────────


@dataclass
class BackgroundProcessInfo:
    """Represents a background process that was spawned via commands.run(background=True).

    Attributes:
        pid: Process ID inside the sandbox.
        sandbox_id: ID of the sandbox where the process is running.

    Example::

        proc = sb.commands.run("npm run dev", background=True)
        print(proc.pid)  # 1234
        proc.kill()
    """

    pid: int
    sandbox_id: str
    _sandbox: Any = field(repr=False, compare=False)

    def kill(self) -> None:
        """Send SIGKILL to the background process."""
        self._sandbox._transport.request(
            "POST",
            f"/sandboxes/{self.sandbox_id}/processes/{self.pid}/signal",
            json_body={"signal": "SIGKILL"},
        )

    def status(self) -> dict[str, Any]:
        """Return the current status of the background process.

        Returns a dict with keys ``pid``, ``state``, ``exit_code`` (when done).
        """
        response = self._sandbox._transport.request(
            "GET", f"/sandboxes/{self.sandbox_id}/processes/{self.pid}"
        )
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return response or {}


@dataclass
class AsyncBackgroundProcessInfo:
    """Async counterpart of :class:`BackgroundProcessInfo`.

    Example::

        proc = await sb.commands.run("npm run dev", background=True)
        await proc.kill()
    """

    pid: int
    sandbox_id: str
    _sandbox: Any = field(repr=False, compare=False)

    async def kill(self) -> None:
        """Send SIGKILL to the background process."""
        await self._sandbox._transport.request(
            "POST",
            f"/sandboxes/{self.sandbox_id}/processes/{self.pid}/signal",
            json_body={"signal": "SIGKILL"},
        )

    async def status(self) -> dict[str, Any]:
        """Return the current status of the background process."""
        response = await self._sandbox._transport.request(
            "GET", f"/sandboxes/{self.sandbox_id}/processes/{self.pid}"
        )
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return response or {}


# ─── Write-files batch item type ─────────────────────────────────────────────


@dataclass
class FileWriteItem:
    """A single file to write in a batch operation.

    Example::

        from miosa.resources.sandbox_namespaces import FileWriteItem
        sb.files.write_files([
            FileWriteItem(path="/workspace/app.py", data="print('hello')"),
            FileWriteItem(path="/workspace/config.json", data=b"{}"),
        ])
    """

    path: str
    data: bytes | str | Path


# ─── File watch event type ────────────────────────────────────────────────────


@dataclass
class FileWatchEvent:
    """A file-system change event yielded by :meth:`SandboxFiles.watch_dir`.

    Attributes:
        event: Change type, e.g. ``"created"``, ``"modified"``, ``"deleted"``, ``"renamed"``.
        path: Absolute path of the affected file or directory.
        is_dir: ``True`` when the path is a directory.
        old_path: Previous path when ``event == "renamed"``, else ``None``.
    """

    event: str
    path: str
    is_dir: bool = False
    old_path: str | None = None


# ─── Git result types ──────────────────────────────────────────────────────────


@dataclass
class GitCloneResult:
    """Result of ``sandbox.git.clone()``.

    Attributes:
        path: Absolute path where the repo was cloned inside the sandbox.
        stdout: Output from the git command.
        stderr: Errors / progress from the git command.
        exit_code: Exit code of the git process.
    """

    path: str
    stdout: str
    stderr: str
    exit_code: int


@dataclass
class GitResult:
    """Result of a git operation (pull, push, commit, etc.).

    Attributes:
        stdout: Output from the git command.
        stderr: Errors / progress from the git command.
        exit_code: Exit code of the git process.
    """

    stdout: str
    stderr: str
    exit_code: int


class SandboxExecRunner:
    """Callable exec namespace for a bound sandbox."""

    def __init__(self, sandbox: Sandbox) -> None:
        self._sandbox = sandbox

    def __call__(self, command: str, opts: ExecOptions | None = None) -> ExecResult:
        return self.run(command, opts)

    def run(self, command: str, opts: ExecOptions | None = None) -> ExecResult:
        return self._sandbox._run_exec(command, opts)

    def stream(self, command: str, opts: ExecOptions | None = None) -> Iterator[SandboxEvent]:
        return self._sandbox.exec_stream(command, opts)


class SandboxCommands:
    """Command helpers for a bound sandbox.

    Example::

        # Blocking exec
        result = sb.commands.run("python3 script.py")

        # Background (non-blocking)
        proc = sb.commands.run("npm run dev", background=True)
        proc.kill()

        # Send stdin to a running process
        sb.commands.send_stdin(proc.pid, "hello\\n")
    """

    def __init__(self, sandbox: Sandbox) -> None:
        self._sandbox = sandbox

    def run(
        self,
        command: str,
        opts: ExecOptions | None = None,
        *,
        background: bool = False,
    ) -> ExecResult | BackgroundProcessInfo:
        """Run a command.

        When ``background=True`` the command is spawned asynchronously and a
        :class:`BackgroundProcessInfo` is returned immediately (non-blocking).
        Otherwise blocks until the command completes and returns :class:`ExecResult`.

        Args:
            command: Shell command to execute.
            opts: Optional exec options (cwd, env, timeout_sec).
            background: When ``True``, spawn in the background and return
                        immediately with a :class:`BackgroundProcessInfo`.

        Example::

            # Blocking
            result = sb.commands.run("echo hello")
            print(result.stdout)

            # Non-blocking
            proc = sb.commands.run("python3 server.py", background=True)
            print(proc.pid)
        """
        if background:
            from .sandboxes import _exec_payload

            response = self._sandbox._transport.request(
                "POST",
                f"/sandboxes/{self._sandbox.id}/processes",
                json_body=_exec_payload(command, opts),
            )
            data: dict[str, Any]
            if isinstance(response, dict) and "data" in response:
                data = response["data"]
            else:
                data = response or {}
            return BackgroundProcessInfo(
                pid=int(data.get("pid", 0)),
                sandbox_id=self._sandbox.id,
                _sandbox=self._sandbox,
            )
        return self._sandbox.exec.run(command, opts)

    def stream(self, command: str, opts: ExecOptions | None = None) -> Iterator[SandboxEvent]:
        return self._sandbox.exec.stream(command, opts)

    def send_stdin(self, pid: int, data: str | bytes) -> None:
        """Write data to the stdin of a background process.

        Args:
            pid: Process ID returned by :meth:`run` when ``background=True``.
            data: Text or bytes to write to the process stdin.

        Example::

            proc = sb.commands.run("python3 -c 'import sys; print(sys.stdin.read())'", background=True)
            sb.commands.send_stdin(proc.pid, "hello\\n")
        """
        if isinstance(data, bytes):
            payload = data.decode("utf-8", errors="replace")
        else:
            payload = data
        self._sandbox._transport.request(
            "POST",
            f"/sandboxes/{self._sandbox.id}/processes/{pid}/stdin",
            json_body={"data": payload},
        )


class SandboxFiles:
    """Filesystem helpers for a bound sandbox.

    Example::

        # Single write
        sb.files.write("/workspace/app.py", "print('hello')")

        # Batch write
        sb.files.write_files([
            {"path": "/workspace/a.py", "data": "# a"},
            {"path": "/workspace/b.py", "data": "# b"},
        ])

        # Directory listing with depth
        entries = sb.files.list("/workspace", depth=2)

        # Watch a directory for changes
        for event in sb.files.watch_dir("/workspace"):
            print(event.event, event.path)
    """

    def __init__(self, sandbox: Sandbox) -> None:
        self._sandbox = sandbox

    def write(self, path: str, content: bytes | str | Path) -> None:
        """Write a single file to the sandbox filesystem."""
        self._sandbox.write_file(path, content)

    def write_files(self, files: list[dict[str, Any] | FileWriteItem]) -> None:
        """Write multiple files in a single request (batch upload).

        Args:
            files: List of ``{"path": str, "data": bytes | str | Path}`` dicts
                   or :class:`FileWriteItem` instances.

        Example::

            sb.files.write_files([
                {"path": "/workspace/app.py", "data": "print(1+1)"},
                {"path": "/workspace/config.json", "data": b"{}"},
            ])
        """
        encoded: list[dict[str, Any]] = []
        for item in files:
            if isinstance(item, FileWriteItem):
                path = item.path
                data: bytes | str | Path = item.data
            else:
                path = item["path"]
                data = item["data"]
            # Encode to base64 regardless of type using the same helper as upload().
            if isinstance(data, Path):
                raw = data.read_bytes()
            elif isinstance(data, str):
                raw = data.encode("utf-8")
            else:
                raw = data
            encoded.append({"path": path, "content": base64.b64encode(raw).decode("ascii")})
        self._sandbox._transport.request(
            "POST",
            f"/sandboxes/{self._sandbox.id}/files/batch",
            json_body={"files": encoded},
        )

    def read(self, path: str) -> bytes:
        """Read a file from the sandbox and return raw bytes."""
        return self._sandbox.download(path)

    def read_text(self, path: str) -> str:
        """Read a file from the sandbox and return UTF-8 text."""
        return self.read(path).decode("utf-8")

    def list(self, path: str = "/workspace", *, depth: int | None = None) -> dict[str, Any]:
        """List files at *path* inside the sandbox.

        Args:
            path: Absolute path to list. Defaults to ``"/workspace"``.
            depth: Maximum directory depth to recurse. ``None`` means server default
                   (typically 1 level). Pass a positive integer to go deeper.

        Example::

            entries = sb.files.list("/workspace", depth=3)
        """
        params: dict[str, Any] = {"path": path}
        if depth is not None:
            params["depth"] = depth
        return self._sandbox.list_files(path, depth=depth)

    def stat(self, path: str) -> dict[str, Any]:
        """Return stat information (size, mode, mtime) for *path*."""
        return self._sandbox.stat_file(path)

    def upload(self, path: str, content: bytes | str | Path) -> None:
        """Alias for :meth:`write`."""
        self.write(path, content)

    def download(self, path: str) -> bytes:
        """Alias for :meth:`read`."""
        return self.read(path)

    def tree(self, path: str = "/workspace", *, depth: int = 3) -> dict[str, Any]:
        """GET /api/v1/sandboxes/{id}/files/tree — recursive directory tree.

        Args:
            path: Root path to tree. Defaults to ``"/workspace"``.
            depth: Maximum recursion depth. Defaults to ``3``.

        Returns:
            Tree node dict with keys ``path``, ``type``, ``name``,
            optional ``size``, ``modified_at``, ``children``.

        Example::

            tree = sb.files.tree("/workspace", depth=2)
        """
        response = self._sandbox._transport.request(
            "GET",
            f"/sandboxes/{self._sandbox.id}/files/tree",
            params={"path": path, "depth": depth},
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response or {}

    def write_many(self, files: list[dict[str, Any]]) -> dict[str, Any]:
        """POST /api/v1/sandboxes/{id}/files/write-many — batch file write.

        Args:
            files: List of ``{"path": str, "content": str | bytes}`` dicts.
                   ``content`` values are auto-base64-encoded when bytes.

        Returns:
            ``{"written": [...], "failed": [...]}``

        Example::

            sb.files.write_many([
                {"path": "/workspace/a.py", "content": "print(1)"},
                {"path": "/workspace/b.py", "content": b"# bytes"},
            ])
        """
        encoded: list[dict[str, Any]] = []
        for item in files:
            raw_content = item.get("content", item.get("data", ""))
            if isinstance(raw_content, bytes):
                b64 = base64.b64encode(raw_content).decode("ascii")
            elif isinstance(raw_content, str):
                b64 = base64.b64encode(raw_content.encode("utf-8")).decode("ascii")
            else:
                b64 = base64.b64encode(str(raw_content).encode("utf-8")).decode("ascii")
            encoded.append({"path": item["path"], "content_base64": b64})
        response = self._sandbox._transport.request(
            "POST",
            f"/sandboxes/{self._sandbox.id}/files/write-many",
            json_body={"files": encoded},
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response or {}

    def watch(self, path: str = "/workspace") -> Iterator[FileWatchEvent]:
        """Alias for :meth:`watch_dir` per contracts (``sandbox.files.watch()``)."""
        return self.watch_dir(path)

    def watch_dir(self, path: str) -> Iterator[FileWatchEvent]:
        """Watch a directory for filesystem change events via SSE.

        Opens a server-sent event stream on ``GET /sandboxes/:id/files/watch``
        and yields :class:`FileWatchEvent` objects until the stream closes or
        the generator is garbage-collected.

        Args:
            path: Absolute path of the directory to watch inside the sandbox.

        Example::

            for event in sb.files.watch_dir("/workspace/src"):
                if event.event == "modified":
                    print(f"File changed: {event.path}")
        """
        import json as _json

        for raw_event in self._sandbox._transport.stream_sse(
            f"/sandboxes/{self._sandbox.id}/files/watch",
            params={"path": path},
        ):
            data_str = raw_event.get("data", "")
            try:
                payload: dict[str, Any] = _json.loads(data_str) if isinstance(data_str, str) else data_str
            except (_json.JSONDecodeError, TypeError):
                continue
            if not isinstance(payload, dict):
                continue
            yield FileWatchEvent(
                event=str(payload.get("event", "modified")),
                path=str(payload.get("path", "")),
                is_dir=bool(payload.get("is_dir", False)),
                old_path=payload.get("old_path"),
            )


class SandboxProcesses:
    """Long-running process management for a bound sandbox.

    Wraps ``/api/v1/sandboxes/{id}/processes`` — start, list, get, stop,
    fetch logs, and stream output of persistent processes.

    Example::

        proc = sb.processes.start("npm run dev", name="dev-server")
        print(proc["pid"])
        for line in sb.processes.stream(proc["pid"]):
            print(line)
        sb.processes.stop(proc["pid"])
    """

    def __init__(self, sandbox: "Sandbox") -> None:
        self._sandbox = sandbox

    def start(
        self,
        command: str,
        *,
        env: dict[str, str] | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """POST /api/v1/sandboxes/{id}/processes — spawn a persistent process."""
        body: dict[str, Any] = {"command": command}
        if env is not None:
            body["env"] = env
        if name is not None:
            body["name"] = name
        response = self._sandbox._transport.request(
            "POST", f"/sandboxes/{self._sandbox.id}/processes", json_body=body
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response or {}

    def list(self) -> list[dict[str, Any]]:
        """GET /api/v1/sandboxes/{id}/processes — list running processes."""
        response = self._sandbox._transport.request(
            "GET", f"/sandboxes/{self._sandbox.id}/processes"
        )
        if isinstance(response, list):
            return response
        if isinstance(response, dict):
            for key in ("data", "processes", "items"):
                val = response.get(key)
                if isinstance(val, list):
                    return val
        return []

    def get(self, pid: int | str) -> dict[str, Any]:
        """GET /api/v1/sandboxes/{id}/processes/{pid}."""
        response = self._sandbox._transport.request(
            "GET", f"/sandboxes/{self._sandbox.id}/processes/{pid}"
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response or {}

    def stop(self, pid: int | str) -> None:
        """DELETE /api/v1/sandboxes/{id}/processes/{pid} — SIGTERM then SIGKILL."""
        self._sandbox._transport.request(
            "DELETE", f"/sandboxes/{self._sandbox.id}/processes/{pid}"
        )

    def logs(self, pid: int | str, *, tail: int = 200) -> str:
        """GET /api/v1/sandboxes/{id}/processes/{pid}/logs?tail=N — fetch log text."""
        response = self._sandbox._transport.request(
            "GET",
            f"/sandboxes/{self._sandbox.id}/processes/{pid}/logs",
            params={"tail": tail},
        )
        if isinstance(response, dict):
            return str(response.get("data") or response.get("logs") or "")
        return str(response or "")

    def stream(self, pid: int | str) -> Iterator[dict[str, Any]]:
        """GET /api/v1/sandboxes/{id}/processes/{pid}/stream (SSE) — live output."""
        import json as _json

        for raw_event in self._sandbox._transport.stream_sse(
            f"/sandboxes/{self._sandbox.id}/processes/{pid}/stream"
        ):
            data_str = raw_event.get("data", "")
            try:
                payload: dict[str, Any] = _json.loads(data_str) if isinstance(data_str, str) else data_str
            except (_json.JSONDecodeError, TypeError):
                payload = {"line": data_str}
            if isinstance(payload, dict):
                yield payload


class SandboxShare:
    """Public share-URL management for a bound sandbox.

    Wraps ``/api/v1/sandboxes/{id}/shares``.

    Example::

        share = sb.share.create(expires_in=3600, scope="read")
        print(share["share_url"])
        sb.share.revoke(share["share_id"])
    """

    def __init__(self, sandbox: "Sandbox") -> None:
        self._sandbox = sandbox

    def create(
        self,
        *,
        expires_in: int | None = None,
        scope: str = "read",
    ) -> dict[str, Any]:
        """POST /api/v1/sandboxes/{id}/shares → {share_id, share_url, expires_at, scope}."""
        body: dict[str, Any] = {"scope": scope}
        if expires_in is not None:
            body["expires_in"] = expires_in
        response = self._sandbox._transport.request(
            "POST", f"/sandboxes/{self._sandbox.id}/shares", json_body=body
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response or {}

    def list(self) -> list[dict[str, Any]]:
        """GET /api/v1/sandboxes/{id}/shares."""
        response = self._sandbox._transport.request(
            "GET", f"/sandboxes/{self._sandbox.id}/shares"
        )
        if isinstance(response, list):
            return response
        if isinstance(response, dict):
            for key in ("data", "shares", "items"):
                val = response.get(key)
                if isinstance(val, list):
                    return val
        return []

    def revoke(self, share_id: str) -> None:
        """DELETE /api/v1/sandboxes/{id}/shares/{share_id}."""
        self._sandbox._transport.request(
            "DELETE", f"/sandboxes/{self._sandbox.id}/shares/{share_id}"
        )


class SandboxPreview:
    """Preview helpers for a bound sandbox.

    Wraps the ``/sandboxes/:id/previews/*`` surface — list, create, show,
    delete, share, and revoke share tokens. ``expose`` is the legacy
    convenience that maps to ``POST /expose``.
    """

    def __init__(self, sandbox: Sandbox) -> None:
        self._sandbox = sandbox

    def expose(self, port: int | None = None) -> str:
        return self._sandbox.expose(port)

    def list(self) -> list[dict[str, Any]]:
        response = self._sandbox._transport.request(
            "GET", f"/sandboxes/{self._sandbox.id}/previews"
        )
        if isinstance(response, list):
            return response
        if isinstance(response, dict):
            for key in ("data", "previews", "items"):
                value = response.get(key)
                if isinstance(value, list):
                    return value
        return []

    def create(self, *, port: int, **opts: Any) -> dict[str, Any]:
        body = {"port": port, **{k: v for k, v in opts.items() if v is not None}}
        response = self._sandbox._transport.request(
            "POST", f"/sandboxes/{self._sandbox.id}/previews", json_body=body
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response

    def get(self, preview_id: str) -> dict[str, Any]:
        response = self._sandbox._transport.request(
            "GET", f"/sandboxes/{self._sandbox.id}/previews/{preview_id}"
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response

    def delete(self, preview_id: str) -> None:
        self._sandbox._transport.request(
            "DELETE", f"/sandboxes/{self._sandbox.id}/previews/{preview_id}"
        )

    def share(
        self,
        preview_id: str,
        *,
        ttl_seconds: int | None = None,
        expires_in_sec: int = 3600,
    ) -> dict[str, Any]:
        """Mint a share token for ``preview_id``."""
        response = self._sandbox._transport.request(
            "POST",
            f"/sandboxes/{self._sandbox.id}/previews/{preview_id}/share",
            json_body={"ttl_seconds": ttl_seconds if ttl_seconds is not None else expires_in_sec},
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response

    def revoke_share(self, preview_id: str) -> None:
        """Invalidate every share token associated with ``preview_id``."""
        self._sandbox._transport.request(
            "DELETE", f"/sandboxes/{self._sandbox.id}/previews/{preview_id}/share"
        )


class SandboxEvents:
    """SSE event stream for a bound sandbox (``GET /sandboxes/:id/events``)."""

    def __init__(self, sandbox: Sandbox) -> None:
        self._sandbox = sandbox

    def stream(self) -> Iterator[dict[str, Any]]:
        """Yield SSE event dicts ``{type, data, id}`` until the stream closes."""
        yield from self._sandbox._transport.stream_sse(
            f"/sandboxes/{self._sandbox.id}/events"
        )


class SandboxEnv:
    """Per-sandbox env-vars.

    Supports full CRUD per the contracts:
    - ``GET /sandboxes/:id/env`` — list all vars
    - ``PUT /sandboxes/:id/env`` — bulk set / replace vars
    - ``DELETE /sandboxes/:id/env/:key`` — delete one var
    """

    def __init__(self, sandbox: Sandbox) -> None:
        self._sandbox = sandbox

    def list(self) -> dict[str, Any]:
        response = self._sandbox._transport.request(
            "GET", f"/sandboxes/{self._sandbox.id}/env"
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response

    # Alias for contracts parity
    get = list

    def set(self, vars: list[dict[str, Any]]) -> dict[str, Any]:
        """PUT /api/v1/sandboxes/{id}/env — bulk-set env vars.

        Args:
            vars: List of ``{"key": str, "value": str, "encrypted"?: bool}``.

        Example::

            sb.env.set([{"key": "DEBUG", "value": "1"}])
        """
        response = self._sandbox._transport.request(
            "PUT", f"/sandboxes/{self._sandbox.id}/env", json_body={"vars": vars}
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response or {}

    def delete(self, key: str) -> None:
        """DELETE /api/v1/sandboxes/{id}/env/{key} — remove one env var."""
        self._sandbox._transport.request(
            "DELETE", f"/sandboxes/{self._sandbox.id}/env/{key}"
        )


class SandboxTerminal:
    """PTY session control (``POST/DELETE /sandboxes/:id/terminal``)."""

    def __init__(self, sandbox: Sandbox) -> None:
        self._sandbox = sandbox

    def create(
        self,
        *,
        cols: int | None = None,
        rows: int | None = None,
        shell: str | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        body = {
            k: v for k, v in {
                "cols": cols,
                "rows": rows,
                "shell": shell,
                "cwd": cwd,
                "env": env,
            }.items() if v is not None
        }
        response = self._sandbox._transport.request(
            "POST", f"/sandboxes/{self._sandbox.id}/terminal", json_body=body
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response

    def delete(self, session_id: str) -> None:
        self._sandbox._transport.request(
            "DELETE", f"/sandboxes/{self._sandbox.id}/terminal/{session_id}"
        )


class SandboxTags:
    """Tag replacement (``PATCH /sandboxes/:id/tags``)."""

    def __init__(self, sandbox: Sandbox) -> None:
        self._sandbox = sandbox

    def set(self, tags: list[str]) -> dict[str, Any]:
        """Replace the full tag list with ``tags``."""
        response = self._sandbox._transport.request(
            "PATCH",
            f"/sandboxes/{self._sandbox.id}/tags",
            json_body={"tags": tags},
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response


class SandboxArtifactsResource:
    """Artifact helpers for a bound sandbox."""

    def __init__(self, sandbox: Sandbox) -> None:
        self._sandbox = sandbox

    def list(self) -> dict[str, Any]:
        return self._sandbox.get_artifacts().data


class SandboxLogs:
    """Log helpers for a bound sandbox."""

    def __init__(self, sandbox: Sandbox) -> None:
        self._sandbox = sandbox

    def get(self, lines: int | None = None) -> dict[str, Any] | str:
        return self._sandbox.get_logs(lines)

    def stream(self) -> Iterator[SandboxEvent]:
        return self._sandbox.stream_logs()


class SandboxSnapshots:
    """Snapshot helpers for a bound sandbox."""

    def __init__(self, sandbox: Sandbox) -> None:
        self._sandbox = sandbox

    def create(self, comment: str | None = None) -> dict[str, Any]:
        return self._sandbox.create_snapshot(comment)

    def list(self) -> list[dict[str, Any]]:
        return self._sandbox.list_snapshots()

    def restore(self, snapshot_id: str) -> Sandbox:
        return self._sandbox.restore_snapshot(snapshot_id)

    def delete(self, snapshot_id: str) -> None:
        self._sandbox.delete_snapshot(snapshot_id)


class SandboxGit:
    """Git convenience helpers for a bound sandbox.

    All operations delegate to git commands executed inside the sandbox.
    The git binary must be present in the sandbox image (it is in all
    ``miosa-sandbox`` images).

    Example::

        sb.git.clone("https://github.com/org/repo", path="/workspace/repo")
        result = sb.git.pull("/workspace/repo")
        sb.git.commit("/workspace/repo", message="auto: updated by agent")
        sb.git.push("/workspace/repo")
    """

    def __init__(self, sandbox: Sandbox) -> None:
        self._sandbox = sandbox

    def _run(self, command: str, cwd: str | None = None) -> GitResult:
        from .sandboxes import ExecOptions, _exec_payload  # local to avoid circular

        opts: ExecOptions | None = {"cwd": cwd} if cwd else None
        result = self._sandbox._run_exec(command, opts)
        return GitResult(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
        )

    def clone(
        self,
        url: str,
        *,
        path: str = "/workspace",
        branch: str | None = None,
        depth: int | None = None,
    ) -> GitCloneResult:
        """Clone a repository into the sandbox.

        Args:
            url: Repository URL (https or ssh).
            path: Destination path inside the sandbox. Defaults to ``"/workspace"``.
            branch: Branch / tag / commit to check out. Defaults to the
                    repository's default branch.
            depth: Shallow clone depth (``--depth N``). ``None`` for a full clone.

        Example::

            result = sb.git.clone("https://github.com/org/repo", path="/workspace/app")
            print(result.exit_code)  # 0 on success
        """
        cmd = ["git", "clone"]
        if branch:
            cmd += ["-b", branch]
        if depth is not None:
            cmd += ["--depth", str(depth)]
        cmd += [url, path]
        result = self._run(" ".join(cmd))
        return GitCloneResult(
            path=path,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
        )

    def pull(self, path: str = "/workspace", *, remote: str = "origin", branch: str = "") -> GitResult:
        """Run ``git pull`` inside *path*.

        Args:
            path: Absolute path of the repo root inside the sandbox.
            remote: Remote name. Defaults to ``"origin"``.
            branch: Branch to pull. Empty string means the tracking branch.

        Example::

            sb.git.pull("/workspace/app")
        """
        cmd = f"git pull {remote}" + (f" {branch}" if branch else "")
        return self._run(cmd, cwd=path)

    def push(
        self,
        path: str = "/workspace",
        *,
        remote: str = "origin",
        branch: str = "",
        force: bool = False,
    ) -> GitResult:
        """Run ``git push`` inside *path*.

        Args:
            path: Absolute path of the repo root inside the sandbox.
            remote: Remote name. Defaults to ``"origin"``.
            branch: Branch to push. Empty string means the tracking branch.
            force: When ``True``, passes ``--force-with-lease``.

        Example::

            sb.git.push("/workspace/app")
        """
        cmd = "git push" + (" --force-with-lease" if force else "")
        cmd += f" {remote}" + (f" {branch}" if branch else "")
        return self._run(cmd.strip(), cwd=path)

    def commit(
        self,
        path: str = "/workspace",
        *,
        message: str,
        add_all: bool = True,
    ) -> GitResult:
        """Stage and commit changes in *path*.

        Args:
            path: Absolute path of the repo root inside the sandbox.
            message: Commit message.
            add_all: When ``True`` (default), runs ``git add -A`` before committing.

        Example::

            sb.git.commit("/workspace/app", message="chore: update deps")
        """
        cmds = []
        if add_all:
            cmds.append("git add -A")
        cmds.append(f"git commit -m {_shell_quote(message)}")
        result = self._run(" && ".join(cmds), cwd=path)
        return result


def _shell_quote(s: str) -> str:
    """Minimal single-quote wrapping for git commit messages."""
    return "'" + s.replace("'", "'\\''") + "'"


# ─── Async Git ────────────────────────────────────────────────────────────────


class AsyncSandboxGit:
    """Async counterpart of :class:`SandboxGit`.

    Example::

        await sb.git.clone("https://github.com/org/repo")
        await sb.git.commit("/workspace", message="auto commit")
    """

    def __init__(self, sandbox: AsyncSandbox) -> None:
        self._sandbox = sandbox

    async def _run(self, command: str, cwd: str | None = None) -> GitResult:
        from .sandboxes import ExecOptions  # local to avoid circular

        opts: ExecOptions | None = {"cwd": cwd} if cwd else None
        result = await self._sandbox._run_exec(command, opts)
        return GitResult(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
        )

    async def clone(
        self,
        url: str,
        *,
        path: str = "/workspace",
        branch: str | None = None,
        depth: int | None = None,
    ) -> GitCloneResult:
        """Async clone a repository into the sandbox."""
        cmd = ["git", "clone"]
        if branch:
            cmd += ["-b", branch]
        if depth is not None:
            cmd += ["--depth", str(depth)]
        cmd += [url, path]
        result = await self._run(" ".join(cmd))
        return GitCloneResult(
            path=path,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
        )

    async def pull(self, path: str = "/workspace", *, remote: str = "origin", branch: str = "") -> GitResult:
        """Async git pull inside *path*."""
        cmd = f"git pull {remote}" + (f" {branch}" if branch else "")
        return await self._run(cmd, cwd=path)

    async def push(
        self,
        path: str = "/workspace",
        *,
        remote: str = "origin",
        branch: str = "",
        force: bool = False,
    ) -> GitResult:
        """Async git push inside *path*."""
        cmd = "git push" + (" --force-with-lease" if force else "")
        cmd += f" {remote}" + (f" {branch}" if branch else "")
        return await self._run(cmd.strip(), cwd=path)

    async def commit(
        self,
        path: str = "/workspace",
        *,
        message: str,
        add_all: bool = True,
    ) -> GitResult:
        """Async stage and commit changes in *path*."""
        cmds = []
        if add_all:
            cmds.append("git add -A")
        cmds.append(f"git commit -m {_shell_quote(message)}")
        return await self._run(" && ".join(cmds), cwd=path)


class AsyncSandboxExecRunner:
    """Callable async exec namespace for a bound sandbox."""

    def __init__(self, sandbox: AsyncSandbox) -> None:
        self._sandbox = sandbox

    async def __call__(self, command: str, opts: ExecOptions | None = None) -> ExecResult:
        return await self.run(command, opts)

    async def run(self, command: str, opts: ExecOptions | None = None) -> ExecResult:
        return await self._sandbox._run_exec(command, opts)

    def stream(
        self, command: str, opts: ExecOptions | None = None
    ) -> AsyncIterator[SandboxEvent]:
        return self._sandbox.exec_stream(command, opts)


class AsyncSandboxCommands:
    """Async command helpers for a bound sandbox.

    Example::

        # Blocking (awaited)
        result = await sb.commands.run("python3 script.py")

        # Background (non-blocking)
        proc = await sb.commands.run("npm run dev", background=True)
        await proc.kill()

        # Send stdin to a running process
        await sb.commands.send_stdin(proc.pid, "hello\\n")
    """

    def __init__(self, sandbox: AsyncSandbox) -> None:
        self._sandbox = sandbox

    async def run(
        self,
        command: str,
        opts: ExecOptions | None = None,
        *,
        background: bool = False,
    ) -> ExecResult | AsyncBackgroundProcessInfo:
        """Run a command.

        When ``background=True`` the command is spawned asynchronously and an
        :class:`AsyncBackgroundProcessInfo` is returned immediately. Otherwise
        awaits completion and returns :class:`ExecResult`.

        Args:
            command: Shell command to execute.
            opts: Optional exec options (cwd, env, timeout_sec).
            background: When ``True``, spawn in the background and return
                        immediately with an :class:`AsyncBackgroundProcessInfo`.
        """
        if background:
            from .sandboxes import _exec_payload

            response = await self._sandbox._transport.request(
                "POST",
                f"/sandboxes/{self._sandbox.id}/processes",
                json_body=_exec_payload(command, opts),
            )
            data: dict[str, Any]
            if isinstance(response, dict) and "data" in response:
                data = response["data"]
            else:
                data = response or {}
            return AsyncBackgroundProcessInfo(
                pid=int(data.get("pid", 0)),
                sandbox_id=self._sandbox.id,
                _sandbox=self._sandbox,
            )
        return await self._sandbox.exec.run(command, opts)

    def stream(
        self, command: str, opts: ExecOptions | None = None
    ) -> AsyncIterator[SandboxEvent]:
        return self._sandbox.exec.stream(command, opts)

    async def send_stdin(self, pid: int, data: str | bytes) -> None:
        """Write data to the stdin of a background process.

        Args:
            pid: Process ID returned by :meth:`run` when ``background=True``.
            data: Text or bytes to write to the process stdin.

        Example::

            await sb.commands.send_stdin(proc.pid, "hello\\n")
        """
        if isinstance(data, bytes):
            payload = data.decode("utf-8", errors="replace")
        else:
            payload = data
        await self._sandbox._transport.request(
            "POST",
            f"/sandboxes/{self._sandbox.id}/processes/{pid}/stdin",
            json_body={"data": payload},
        )


class AsyncSandboxFiles:
    """Async filesystem helpers for a bound sandbox.

    Example::

        await sb.files.write("/workspace/app.py", "print('hello')")

        await sb.files.write_files([
            {"path": "/workspace/a.py", "data": "# a"},
            {"path": "/workspace/b.py", "data": "# b"},
        ])

        async for event in sb.files.watch_dir("/workspace"):
            print(event.event, event.path)
    """

    def __init__(self, sandbox: AsyncSandbox) -> None:
        self._sandbox = sandbox

    async def write(self, path: str, content: bytes | str | Path) -> None:
        """Write a single file to the sandbox filesystem."""
        await self._sandbox.write_file(path, content)

    async def write_files(self, files: list[dict[str, Any] | FileWriteItem]) -> None:
        """Write multiple files in a single batch request.

        Args:
            files: List of ``{"path": str, "data": bytes | str | Path}`` dicts
                   or :class:`FileWriteItem` instances.

        Example::

            await sb.files.write_files([
                {"path": "/workspace/app.py", "data": "print(1+1)"},
                {"path": "/workspace/config.json", "data": b"{}"},
            ])
        """
        encoded: list[dict[str, Any]] = []
        for item in files:
            if isinstance(item, FileWriteItem):
                path = item.path
                data: bytes | str | Path = item.data
            else:
                path = item["path"]
                data = item["data"]
            if isinstance(data, Path):
                raw = data.read_bytes()
            elif isinstance(data, str):
                raw = data.encode("utf-8")
            else:
                raw = data
            encoded.append({"path": path, "content": base64.b64encode(raw).decode("ascii")})
        await self._sandbox._transport.request(
            "POST",
            f"/sandboxes/{self._sandbox.id}/files/batch",
            json_body={"files": encoded},
        )

    async def read(self, path: str) -> bytes:
        """Read a file from the sandbox and return raw bytes."""
        return await self._sandbox.download(path)

    async def read_text(self, path: str) -> str:
        """Read a file from the sandbox and return UTF-8 text."""
        return (await self.read(path)).decode("utf-8")

    async def list(self, path: str = "/workspace", *, depth: int | None = None) -> dict[str, Any]:
        """List files at *path* inside the sandbox.

        Args:
            path: Absolute path to list. Defaults to ``"/workspace"``.
            depth: Maximum directory depth to recurse. ``None`` means server default.

        Example::

            entries = await sb.files.list("/workspace", depth=2)
        """
        return await self._sandbox.list_files(path, depth=depth)

    async def stat(self, path: str) -> dict[str, Any]:
        """Return stat information for *path*."""
        return await self._sandbox.stat_file(path)

    async def upload(self, path: str, content: bytes | str | Path) -> None:
        """Alias for :meth:`write`."""
        await self.write(path, content)

    async def download(self, path: str) -> bytes:
        """Alias for :meth:`read`."""
        return await self.read(path)

    async def tree(self, path: str = "/workspace", *, depth: int = 3) -> dict[str, Any]:
        """GET /api/v1/sandboxes/{id}/files/tree."""
        response = await self._sandbox._transport.request(
            "GET",
            f"/sandboxes/{self._sandbox.id}/files/tree",
            params={"path": path, "depth": depth},
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response or {}

    async def write_many(self, files: list[dict[str, Any]]) -> dict[str, Any]:
        """POST /api/v1/sandboxes/{id}/files/write-many — batch file write."""
        encoded: list[dict[str, Any]] = []
        for item in files:
            raw_content = item.get("content", item.get("data", ""))
            if isinstance(raw_content, bytes):
                b64 = base64.b64encode(raw_content).decode("ascii")
            elif isinstance(raw_content, str):
                b64 = base64.b64encode(raw_content.encode("utf-8")).decode("ascii")
            else:
                b64 = base64.b64encode(str(raw_content).encode("utf-8")).decode("ascii")
            encoded.append({"path": item["path"], "content_base64": b64})
        response = await self._sandbox._transport.request(
            "POST",
            f"/sandboxes/{self._sandbox.id}/files/write-many",
            json_body={"files": encoded},
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response or {}

    async def watch_dir(self, path: str) -> AsyncIterator[FileWatchEvent]:
        """Watch a directory for filesystem change events via SSE.

        Opens an SSE stream on ``GET /sandboxes/:id/files/watch`` and
        yields :class:`FileWatchEvent` objects.

        Args:
            path: Absolute path of the directory to watch inside the sandbox.

        Example::

            async for event in sb.files.watch_dir("/workspace/src"):
                print(event.event, event.path)
        """
        import json as _json

        async for raw_event in self._sandbox._transport.stream_sse(
            f"/sandboxes/{self._sandbox.id}/files/watch",
            params={"path": path},
        ):
            data_str = raw_event.get("data", "")
            try:
                payload: dict[str, Any] = _json.loads(data_str) if isinstance(data_str, str) else data_str
            except (_json.JSONDecodeError, TypeError):
                continue
            if not isinstance(payload, dict):
                continue
            yield FileWatchEvent(
                event=str(payload.get("event", "modified")),
                path=str(payload.get("path", "")),
                is_dir=bool(payload.get("is_dir", False)),
                old_path=payload.get("old_path"),
            )

    async def watch(self, path: str = "/workspace") -> AsyncIterator[FileWatchEvent]:
        """Alias for :meth:`watch_dir` per contracts."""
        async for event in self.watch_dir(path):
            yield event


class AsyncSandboxProcesses:
    """Async long-running process management for a bound sandbox."""

    def __init__(self, sandbox: "AsyncSandbox") -> None:
        self._sandbox = sandbox

    async def start(
        self,
        command: str,
        *,
        env: dict[str, str] | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"command": command}
        if env is not None:
            body["env"] = env
        if name is not None:
            body["name"] = name
        response = await self._sandbox._transport.request(
            "POST", f"/sandboxes/{self._sandbox.id}/processes", json_body=body
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response or {}

    async def list(self) -> list[dict[str, Any]]:
        response = await self._sandbox._transport.request(
            "GET", f"/sandboxes/{self._sandbox.id}/processes"
        )
        if isinstance(response, list):
            return response
        if isinstance(response, dict):
            for key in ("data", "processes", "items"):
                val = response.get(key)
                if isinstance(val, list):
                    return val
        return []

    async def get(self, pid: int | str) -> dict[str, Any]:
        response = await self._sandbox._transport.request(
            "GET", f"/sandboxes/{self._sandbox.id}/processes/{pid}"
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response or {}

    async def stop(self, pid: int | str) -> None:
        await self._sandbox._transport.request(
            "DELETE", f"/sandboxes/{self._sandbox.id}/processes/{pid}"
        )

    async def logs(self, pid: int | str, *, tail: int = 200) -> str:
        response = await self._sandbox._transport.request(
            "GET",
            f"/sandboxes/{self._sandbox.id}/processes/{pid}/logs",
            params={"tail": tail},
        )
        if isinstance(response, dict):
            return str(response.get("data") or response.get("logs") or "")
        return str(response or "")

    async def stream(self, pid: int | str) -> AsyncIterator[dict[str, Any]]:
        import json as _json

        async for raw_event in self._sandbox._transport.stream_sse(
            f"/sandboxes/{self._sandbox.id}/processes/{pid}/stream"
        ):
            data_str = raw_event.get("data", "")
            try:
                payload: dict[str, Any] = _json.loads(data_str) if isinstance(data_str, str) else data_str
            except (_json.JSONDecodeError, TypeError):
                payload = {"line": data_str}
            if isinstance(payload, dict):
                yield payload


class AsyncSandboxShare:
    """Async public share-URL management for a bound sandbox."""

    def __init__(self, sandbox: "AsyncSandbox") -> None:
        self._sandbox = sandbox

    async def create(
        self,
        *,
        expires_in: int | None = None,
        scope: str = "read",
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"scope": scope}
        if expires_in is not None:
            body["expires_in"] = expires_in
        response = await self._sandbox._transport.request(
            "POST", f"/sandboxes/{self._sandbox.id}/shares", json_body=body
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response or {}

    async def list(self) -> list[dict[str, Any]]:
        response = await self._sandbox._transport.request(
            "GET", f"/sandboxes/{self._sandbox.id}/shares"
        )
        if isinstance(response, list):
            return response
        if isinstance(response, dict):
            for key in ("data", "shares", "items"):
                val = response.get(key)
                if isinstance(val, list):
                    return val
        return []

    async def revoke(self, share_id: str) -> None:
        await self._sandbox._transport.request(
            "DELETE", f"/sandboxes/{self._sandbox.id}/shares/{share_id}"
        )


class AsyncSandboxPreview:
    """Async preview helpers for a bound sandbox."""

    def __init__(self, sandbox: AsyncSandbox) -> None:
        self._sandbox = sandbox

    async def expose(self, port: int | None = None) -> str:
        return await self._sandbox.expose(port)

    async def list(self) -> list[dict[str, Any]]:
        response = await self._sandbox._transport.request(
            "GET", f"/sandboxes/{self._sandbox.id}/previews"
        )
        if isinstance(response, list):
            return response
        if isinstance(response, dict):
            for key in ("data", "previews", "items"):
                value = response.get(key)
                if isinstance(value, list):
                    return value
        return []

    async def create(self, *, port: int, **opts: Any) -> dict[str, Any]:
        body = {"port": port, **{k: v for k, v in opts.items() if v is not None}}
        response = await self._sandbox._transport.request(
            "POST", f"/sandboxes/{self._sandbox.id}/previews", json_body=body
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response

    async def get(self, preview_id: str) -> dict[str, Any]:
        response = await self._sandbox._transport.request(
            "GET", f"/sandboxes/{self._sandbox.id}/previews/{preview_id}"
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response

    async def delete(self, preview_id: str) -> None:
        await self._sandbox._transport.request(
            "DELETE", f"/sandboxes/{self._sandbox.id}/previews/{preview_id}"
        )

    async def share(
        self,
        preview_id: str,
        *,
        ttl_seconds: int | None = None,
        expires_in_sec: int = 3600,
    ) -> dict[str, Any]:
        response = await self._sandbox._transport.request(
            "POST",
            f"/sandboxes/{self._sandbox.id}/previews/{preview_id}/share",
            json_body={"ttl_seconds": ttl_seconds if ttl_seconds is not None else expires_in_sec},
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response

    async def revoke_share(self, preview_id: str) -> None:
        await self._sandbox._transport.request(
            "DELETE", f"/sandboxes/{self._sandbox.id}/previews/{preview_id}/share"
        )


class AsyncSandboxEvents:
    """Async SSE event stream for a sandbox."""

    def __init__(self, sandbox: AsyncSandbox) -> None:
        self._sandbox = sandbox

    async def stream(self) -> AsyncIterator[dict[str, Any]]:
        async for event in self._sandbox._transport.stream_sse(
            f"/sandboxes/{self._sandbox.id}/events"
        ):
            yield event


class AsyncSandboxEnv:
    """Async per-sandbox env-vars — full CRUD."""

    def __init__(self, sandbox: AsyncSandbox) -> None:
        self._sandbox = sandbox

    async def list(self) -> dict[str, Any]:
        response = await self._sandbox._transport.request(
            "GET", f"/sandboxes/{self._sandbox.id}/env"
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response

    get = list  # contracts alias

    async def set(self, vars: list[dict[str, Any]]) -> dict[str, Any]:
        """PUT /api/v1/sandboxes/{id}/env — bulk-set env vars."""
        response = await self._sandbox._transport.request(
            "PUT", f"/sandboxes/{self._sandbox.id}/env", json_body={"vars": vars}
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response or {}

    async def delete(self, key: str) -> None:
        """DELETE /api/v1/sandboxes/{id}/env/{key}."""
        await self._sandbox._transport.request(
            "DELETE", f"/sandboxes/{self._sandbox.id}/env/{key}"
        )


class AsyncSandboxTerminal:
    """Async sandbox PTY session control."""

    def __init__(self, sandbox: AsyncSandbox) -> None:
        self._sandbox = sandbox

    async def create(
        self,
        *,
        cols: int | None = None,
        rows: int | None = None,
        shell: str | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        body = {
            k: v for k, v in {
                "cols": cols,
                "rows": rows,
                "shell": shell,
                "cwd": cwd,
                "env": env,
            }.items() if v is not None
        }
        response = await self._sandbox._transport.request(
            "POST", f"/sandboxes/{self._sandbox.id}/terminal", json_body=body
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response

    async def delete(self, session_id: str) -> None:
        await self._sandbox._transport.request(
            "DELETE", f"/sandboxes/{self._sandbox.id}/terminal/{session_id}"
        )


class AsyncSandboxTags:
    """Async sandbox tag replacement."""

    def __init__(self, sandbox: AsyncSandbox) -> None:
        self._sandbox = sandbox

    async def set(self, tags: list[str]) -> dict[str, Any]:
        response = await self._sandbox._transport.request(
            "PATCH",
            f"/sandboxes/{self._sandbox.id}/tags",
            json_body={"tags": tags},
        )
        if isinstance(response, dict) and "data" in response and len(response) <= 2:
            return response["data"]
        return response


class AsyncSandboxArtifactsResource:
    """Async artifact helpers for a bound sandbox."""

    def __init__(self, sandbox: AsyncSandbox) -> None:
        self._sandbox = sandbox

    async def list(self) -> dict[str, Any]:
        return (await self._sandbox.get_artifacts()).data


class AsyncSandboxLogs:
    """Async log helpers for a bound sandbox."""

    def __init__(self, sandbox: AsyncSandbox) -> None:
        self._sandbox = sandbox

    async def get(self, lines: int | None = None) -> dict[str, Any] | str:
        return await self._sandbox.get_logs(lines)

    def stream(self) -> AsyncIterator[SandboxEvent]:
        return self._sandbox.stream_logs()


class AsyncSandboxSnapshots:
    """Async snapshot helpers for a bound sandbox."""

    def __init__(self, sandbox: AsyncSandbox) -> None:
        self._sandbox = sandbox

    async def create(self, comment: str | None = None) -> dict[str, Any]:
        return await self._sandbox.create_snapshot(comment)

    async def list(self) -> list[dict[str, Any]]:
        return await self._sandbox.list_snapshots()

    async def restore(self, snapshot_id: str) -> AsyncSandbox:
        return await self._sandbox.restore_snapshot(snapshot_id)

    async def delete(self, snapshot_id: str) -> None:
        await self._sandbox.delete_snapshot(snapshot_id)


__all__ = [
    # Sync namespace classes
    "SandboxArtifactsResource",
    "SandboxCommands",
    "SandboxEnv",
    "SandboxEvents",
    "SandboxExecRunner",
    "SandboxFiles",
    "SandboxGit",
    "SandboxLogs",
    "SandboxPreview",
    "SandboxProcesses",
    "SandboxShare",
    "SandboxSnapshots",
    "SandboxTags",
    "SandboxTerminal",
    # Async namespace classes
    "AsyncSandboxArtifactsResource",
    "AsyncSandboxCommands",
    "AsyncSandboxEnv",
    "AsyncSandboxEvents",
    "AsyncSandboxExecRunner",
    "AsyncSandboxFiles",
    "AsyncSandboxGit",
    "AsyncSandboxLogs",
    "AsyncSandboxPreview",
    "AsyncSandboxProcesses",
    "AsyncSandboxShare",
    "AsyncSandboxSnapshots",
    "AsyncSandboxTags",
    "AsyncSandboxTerminal",
    # Result / value types
    "AsyncBackgroundProcessInfo",
    "BackgroundProcessInfo",
    "FileWatchEvent",
    "FileWriteItem",
    "GitCloneResult",
    "GitResult",
]
