"""Real-time event subscription for a Computer.

Accessed via ``computer.events``. Opens a WebSocket to the event stream and
yields typed :class:`~miosa.types.ComputerEvent` payloads. Producers that
can be subscribed to: ``window``, ``clipboard``, ``file``, ``process``, ``idle``.

Example — async::

    stream = await computer.events.subscribe(["file", "process"])
    async for event in stream:
        print(event.type, event.payload)

Requires the ``websockets`` package. Install with::

    pip install miosa[events]
"""

from __future__ import annotations

import asyncio
import json as _json
from collections.abc import AsyncIterator, Iterator, Sequence
from typing import (
    TYPE_CHECKING,
    Any,
    List,
    Optional,
)
from urllib.parse import urlencode

from ..types import ComputerEvent

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


# Valid producer names (mirrors the TS ``EventProducer`` union).
EVENT_PRODUCERS = ("window", "clipboard", "file", "process", "idle")


def _build_ws_url(
    base_url: str,
    computer_id: str,
    subscribe: Sequence[str],
    paths: Optional[Sequence[str]],
    idle_threshold_sec: Optional[int],
) -> str:
    """Translate the HTTP base URL into a ``ws(s)://`` events endpoint."""
    ws_base = base_url
    if ws_base.startswith("https://"):
        ws_base = "wss://" + ws_base[len("https://"):]
    elif ws_base.startswith("http://"):
        ws_base = "ws://" + ws_base[len("http://"):]
    ws_base = ws_base.rstrip("/")

    params: dict = {"subscribe": ",".join(subscribe)}
    if paths:
        params["paths"] = ",".join(paths)
    if idle_threshold_sec is not None:
        params["idle_threshold_sec"] = str(idle_threshold_sec)

    return f"{ws_base}/computers/{computer_id}/events?{urlencode(params)}"


def _parse_frame(raw: Any) -> Optional[ComputerEvent]:
    """Decode a WS text frame into a :class:`ComputerEvent`. ``None`` on bad frame."""
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError:
            return None
    if not isinstance(raw, str):
        return None
    try:
        parsed = _json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    return ComputerEvent.model_validate(parsed)


def _validate_subscribe(subscribe: Sequence[str]) -> List[str]:
    if not subscribe:
        raise ValueError(
            "subscribe must contain at least one producer name "
            f"(one of {EVENT_PRODUCERS})"
        )
    bad = [p for p in subscribe if p not in EVENT_PRODUCERS]
    if bad:
        raise ValueError(
            f"unknown event producer(s): {bad}; valid: {EVENT_PRODUCERS}"
        )
    return list(subscribe)


# ───────────────────────────────────────────────────────────────────────────
# EventStream (wraps a websocket connection)
# ───────────────────────────────────────────────────────────────────────────

class EventStream:
    """Async-iterable WebSocket event stream.

    Yields :class:`~miosa.types.ComputerEvent` objects until the server
    closes the stream or :meth:`close` is called. Malformed frames are
    dropped silently.

    Example::

        stream = await computer.events.subscribe(["file"])
        async for event in stream:
            print(event.type, event.payload)
        await stream.close()
    """

    def __init__(self, ws: Any) -> None:
        self._ws = ws
        self._closed = False

    def __aiter__(self) -> EventStream:
        return self

    async def __anext__(self) -> ComputerEvent:
        while True:
            if self._closed or self._ws is None:
                raise StopAsyncIteration
            try:
                raw = await self._ws.recv()
            except Exception:  # connection closed / any error terminates stream
                self._closed = True
                raise StopAsyncIteration
            event = _parse_frame(raw)
            if event is not None:
                return event

    async def close(self) -> None:
        """Close the underlying WebSocket. Idempotent."""
        if self._closed or self._ws is None:
            return
        self._closed = True
        try:
            await self._ws.close()
        except Exception:
            pass
        self._ws = None

    @property
    def is_closed(self) -> bool:
        return self._closed


# ───────────────────────────────────────────────────────────────────────────
# Events resource
# ───────────────────────────────────────────────────────────────────────────

def _load_websockets():
    """Lazy-import the ``websockets`` package. Raises a helpful error if missing."""
    try:
        import websockets  # type: ignore

        return websockets
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "The `websockets` package is required for real-time events. "
            "Install it with: pip install websockets"
        ) from exc


class Events:
    """Synchronous wrapper — delegates to the async implementation.

    Use :class:`AsyncEvents` directly in async code for best ergonomics.
    """

    def __init__(
        self, transport: SyncTransport, computer_id: str
    ) -> None:
        self._transport = transport
        self._computer_id = computer_id

    @property
    def _api_key(self) -> str:
        return self._transport._api_key  # type: ignore[attr-defined]

    @property
    def _base_url(self) -> str:
        return self._transport._base_url  # type: ignore[attr-defined]

    def subscribe(
        self,
        types: Sequence[str],
        *,
        paths: Optional[Sequence[str]] = None,
        idle_threshold_sec: int = 30,
    ) -> Iterator[ComputerEvent]:
        """Open a subscription and yield events synchronously.

        Internally drives an event loop — each call blocks until a new
        event arrives or the stream closes. Use :class:`AsyncEvents` in
        async code.
        """
        subscribe = _validate_subscribe(types)
        ws_url = _build_ws_url(
            self._base_url,
            self._computer_id,
            subscribe,
            paths,
            idle_threshold_sec,
        )
        api_key = self._api_key

        loop = asyncio.new_event_loop()
        try:
            ws = loop.run_until_complete(_connect_ws(ws_url, api_key))
            try:
                while True:
                    try:
                        raw = loop.run_until_complete(ws.recv())
                    except Exception:
                        return
                    event = _parse_frame(raw)
                    if event is not None:
                        yield event
            finally:
                try:
                    loop.run_until_complete(ws.close())
                except Exception:
                    pass
        finally:
            loop.close()


class AsyncEvents:
    """Asynchronous event subscription — returns an :class:`EventStream`."""

    def __init__(
        self, transport: AsyncTransport, computer_id: str
    ) -> None:
        self._transport = transport
        self._computer_id = computer_id

    @property
    def _api_key(self) -> str:
        return self._transport._api_key  # type: ignore[attr-defined]

    @property
    def _base_url(self) -> str:
        return self._transport._base_url  # type: ignore[attr-defined]

    async def subscribe(
        self,
        types: Sequence[str],
        *,
        paths: Optional[Sequence[str]] = None,
        idle_threshold_sec: int = 30,
    ) -> EventStream:
        """Open a WebSocket subscription for the given producers.

        ``types`` — at least one of ``"window" | "clipboard" | "file" |
        "process" | "idle"``.

        Example::

            stream = await computer.events.subscribe(
                ["window", "file"],
                paths=["/workspace"],
            )
            async for event in stream:
                print(event.type, event.payload)
        """
        subscribe = _validate_subscribe(types)
        ws_url = _build_ws_url(
            self._base_url,
            self._computer_id,
            subscribe,
            paths,
            idle_threshold_sec,
        )
        ws = await _connect_ws(ws_url, self._api_key)
        return EventStream(ws)

    async def iterate(
        self,
        types: Sequence[str],
        *,
        paths: Optional[Sequence[str]] = None,
        idle_threshold_sec: int = 30,
    ) -> AsyncIterator[ComputerEvent]:
        """Convenience wrapper — ``async for event in events.iterate(...)``."""
        stream = await self.subscribe(
            types, paths=paths, idle_threshold_sec=idle_threshold_sec
        )
        try:
            async for event in stream:
                yield event
        finally:
            await stream.close()


async def _connect_ws(url: str, api_key: str) -> Any:
    """Open a WebSocket connection with ``Authorization: Bearer <key>`` header."""
    ws_pkg = _load_websockets()
    # ``websockets`` 14+ supports ``additional_headers`` in the modern
    # client; older releases use ``extra_headers``. Try both.
    headers = [("Authorization", f"Bearer {api_key}")]
    connect = getattr(ws_pkg, "connect", None)
    if connect is None:  # pragma: no cover
        raise RuntimeError("websockets.connect not available")
    try:
        return await connect(url, additional_headers=headers)
    except TypeError:
        return await connect(url, extra_headers=headers)
