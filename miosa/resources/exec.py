"""Command execution resource — bash and python on the computer.

Also exposes :meth:`ExecResource.spawn` for long-running interactive processes
streamed over a WebSocket (see :class:`ExecProcess`).
"""

from __future__ import annotations

import asyncio
import json as _json
from collections.abc import AsyncIterator, Sequence
from typing import TYPE_CHECKING, Any, Dict, Optional, Union
from urllib.parse import urlencode

from ..types import ExecRequest, ExecResult, PythonExecRequest

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


# ───────────────────────────────────────────────────────────────────────────
# ExecProcess — WebSocket-backed interactive process handle
# ───────────────────────────────────────────────────────────────────────────

def _build_spawn_ws_url(
    base_url: str, computer_id: str, query: Dict[str, str]
) -> str:
    ws_base = base_url
    if ws_base.startswith("https://"):
        ws_base = "wss://" + ws_base[len("https://"):]
    elif ws_base.startswith("http://"):
        ws_base = "ws://" + ws_base[len("http://"):]
    ws_base = ws_base.rstrip("/")
    return (
        f"{ws_base}/computers/{computer_id}/exec/stream?"
        + urlencode({k: v for k, v in query.items() if v is not None})
    )


async def _connect_spawn_ws(url: str, api_key: str) -> Any:
    try:
        import websockets  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "The `websockets` package is required for exec.spawn(). "
            "Install it with: pip install websockets"
        ) from exc
    headers = [("Authorization", f"Bearer {api_key}")]
    try:
        return await websockets.connect(url, additional_headers=headers)
    except TypeError:
        return await websockets.connect(url, extra_headers=headers)


class ExecProcess:
    """An interactive process spawned via :meth:`ExecResource.spawn`.

    Messages received from the VM are decoded as JSON frames of the form
    ``{"type": "stdout"|"stderr"|"exit", "data": "..."}``. Writes to stdin
    are sent as ``{"type": "stdin", "data": "..."}``.
    """

    def __init__(self, ws: Any) -> None:
        self._ws = ws
        self._closed = False
        self._exit_code: Optional[int] = None
        # Buffered lines per stream so ``stdout`` / ``stderr`` iterators can
        # coexist and multiplex a single WS.
        self._stdout_q: asyncio.Queue[str] = asyncio.Queue()
        self._stderr_q: asyncio.Queue[str] = asyncio.Queue()
        self._exit_evt: asyncio.Event = asyncio.Event()
        self._reader_task: Optional[asyncio.Task[None]] = None

    def _ensure_reader(self) -> None:
        if self._reader_task is None or self._reader_task.done():
            self._reader_task = asyncio.ensure_future(self._read_loop())

    async def _read_loop(self) -> None:
        try:
            while not self._closed and self._ws is not None:
                raw = await self._ws.recv()
                if isinstance(raw, (bytes, bytearray)):
                    try:
                        raw = raw.decode("utf-8")
                    except UnicodeDecodeError:
                        continue
                try:
                    frame = _json.loads(raw)
                except (ValueError, TypeError):
                    continue
                if not isinstance(frame, dict):
                    continue
                kind = frame.get("type")
                data = frame.get("data", "")
                if kind == "stdout":
                    await self._stdout_q.put(data)
                elif kind == "stderr":
                    await self._stderr_q.put(data)
                elif kind == "exit":
                    try:
                        self._exit_code = int(frame.get("code", 0))
                    except (TypeError, ValueError):
                        self._exit_code = 0
                    self._exit_evt.set()
                    break
        except Exception:
            self._exit_evt.set()

    async def stdout(self) -> AsyncIterator[str]:
        """Async-iterate stdout chunks until the process exits."""
        self._ensure_reader()
        while True:
            if self._stdout_q.empty() and self._exit_evt.is_set():
                return
            get_task = asyncio.ensure_future(self._stdout_q.get())
            exit_task = asyncio.ensure_future(self._exit_evt.wait())
            done, pending = await asyncio.wait(
                {get_task, exit_task}, return_when=asyncio.FIRST_COMPLETED
            )
            for p in pending:
                p.cancel()
            if get_task in done:
                yield get_task.result()
                continue
            if not self._stdout_q.empty():
                yield await self._stdout_q.get()
                continue
            return

    async def stderr(self) -> AsyncIterator[str]:
        """Async-iterate stderr chunks until the process exits."""
        self._ensure_reader()
        while True:
            if self._stderr_q.empty() and self._exit_evt.is_set():
                return
            get_task = asyncio.ensure_future(self._stderr_q.get())
            exit_task = asyncio.ensure_future(self._exit_evt.wait())
            done, pending = await asyncio.wait(
                {get_task, exit_task}, return_when=asyncio.FIRST_COMPLETED
            )
            for p in pending:
                p.cancel()
            if get_task in done:
                yield get_task.result()
                continue
            if not self._stderr_q.empty():
                yield await self._stderr_q.get()
                continue
            return

    async def write(self, data: Union[str, bytes]) -> None:
        """Write to the process stdin."""
        if self._closed or self._ws is None:
            raise RuntimeError("process is closed")
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        frame = _json.dumps({"type": "stdin", "data": data})
        await self._ws.send(frame)

    async def close_stdin(self) -> None:
        """Send EOF to stdin."""
        if self._closed or self._ws is None:
            return
        await self._ws.send(_json.dumps({"type": "stdin_close"}))

    async def resize(self, rows: int, cols: int) -> None:
        """Resize the pty associated with the process."""
        if self._closed or self._ws is None:
            raise RuntimeError("process is closed")
        frame = _json.dumps({"type": "resize", "rows": int(rows), "cols": int(cols)})
        await self._ws.send(frame)

    async def wait(self) -> int:
        """Block until the process exits. Returns its exit code."""
        self._ensure_reader()
        await self._exit_evt.wait()
        return self._exit_code or 0

    async def kill(self) -> None:
        """Send a kill signal and close the connection."""
        if self._closed or self._ws is None:
            return
        try:
            await self._ws.send(_json.dumps({"type": "signal", "signal": "SIGKILL"}))
        except Exception:
            pass
        await self.close()

    async def close(self) -> None:
        """Close the underlying WebSocket. Idempotent."""
        if self._closed:
            return
        self._closed = True
        self._exit_evt.set()
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None


# ───────────────────────────────────────────────────────────────────────────
# ExecResource
# ───────────────────────────────────────────────────────────────────────────


class ExecResource:
    """Synchronous command execution."""

    def __init__(self, transport: SyncTransport, computer_id: str) -> None:
        self._transport = transport
        self._computer_id = computer_id

    def bash(self, command: str, *, timeout: Optional[int] = None) -> ExecResult:
        """Execute a bash command on the computer."""
        body = ExecRequest(command=command, timeout=timeout)
        data = self._transport.request(
            "POST",
            f"/computers/{self._computer_id}/exec",
            json_body=body.model_dump(exclude_none=True),
        )
        return ExecResult.model_validate(data)

    def python(self, code: str, *, timeout: Optional[int] = None) -> ExecResult:
        """Execute Python code on the computer."""
        body = PythonExecRequest(code=code, timeout=timeout)
        data = self._transport.request(
            "POST",
            f"/computers/{self._computer_id}/exec/python",
            json_body=body.model_dump(exclude_none=True),
        )
        return ExecResult.model_validate(data)

    def spawn(
        self,
        command: str,
        *,
        args: Optional[Sequence[str]] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        rows: Optional[int] = None,
        cols: Optional[int] = None,
    ) -> "ExecProcess":
        """Not supported on the synchronous client.

        WebSocket connections require an async event loop. Use
        :class:`AsyncExecResource` (available via ``AsyncMiosa``) instead::

            async with AsyncMiosa(api_key=...) as client:
                proc = await client.computers.get("...").exec.spawn("bash")
        """
        raise NotImplementedError(
            "spawn() requires AsyncExecResource. "
            "Use AsyncMiosa instead of Miosa."
        )


class AsyncExecResource:
    """Asynchronous command execution."""

    def __init__(self, transport: AsyncTransport, computer_id: str) -> None:
        self._transport = transport
        self._computer_id = computer_id

    async def bash(self, command: str, *, timeout: Optional[int] = None) -> ExecResult:
        body = ExecRequest(command=command, timeout=timeout)
        data = await self._transport.request(
            "POST",
            f"/computers/{self._computer_id}/exec",
            json_body=body.model_dump(exclude_none=True),
        )
        return ExecResult.model_validate(data)

    async def python(self, code: str, *, timeout: Optional[int] = None) -> ExecResult:
        body = PythonExecRequest(code=code, timeout=timeout)
        data = await self._transport.request(
            "POST",
            f"/computers/{self._computer_id}/exec/python",
            json_body=body.model_dump(exclude_none=True),
        )
        return ExecResult.model_validate(data)

    async def spawn(
        self,
        command: str,
        *,
        args: Optional[Sequence[str]] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        rows: Optional[int] = None,
        cols: Optional[int] = None,
    ) -> ExecProcess:
        """Spawn a long-running interactive process over a WebSocket."""
        api_key = self._transport._api_key  # type: ignore[attr-defined]
        base_url = self._transport._base_url  # type: ignore[attr-defined]
        query: Dict[str, str] = {"command": command}
        if args:
            query["args"] = ",".join(args)
        if cwd is not None:
            query["cwd"] = cwd
        if env is not None:
            query["env"] = _json.dumps(env)
        if rows is not None:
            query["rows"] = str(rows)
        if cols is not None:
            query["cols"] = str(cols)
        ws_url = _build_spawn_ws_url(base_url, self._computer_id, query)
        ws = await _connect_spawn_ws(ws_url, api_key)
        return ExecProcess(ws)
