"""Tests for real-time events and exec.spawn WebSocket surfaces.

These tests don't open real WebSocket connections — instead they verify
the URL construction, frame parsing, and resize framing with a fake
``websocket`` object.
"""

from __future__ import annotations

import json

import pytest

from miosa.resources.events import (
    EventStream,
    _build_ws_url,
    _parse_frame,
    _validate_subscribe,
)
from miosa.resources.exec import ExecProcess, _build_spawn_ws_url
from miosa.types import ComputerEvent

# ───────────────────────────────────────────────────────────────────────────
# URL construction
# ───────────────────────────────────────────────────────────────────────────


class TestEventsUrl:
    def test_https_base_rewritten_to_wss(self):
        url = _build_ws_url(
            "https://api.miosa.ai/api/v1",
            "comp_1",
            ["file", "window"],
            None,
            None,
        )
        assert url.startswith("wss://api.miosa.ai/api/v1/computers/comp_1/events?")
        assert "subscribe=file%2Cwindow" in url

    def test_paths_and_idle_threshold_encoded(self):
        url = _build_ws_url(
            "https://api.miosa.ai/api/v1",
            "comp_1",
            ["file"],
            ["/workspace", "/home/user"],
            60,
        )
        assert "paths=%2Fworkspace%2C%2Fhome%2Fuser" in url
        assert "idle_threshold_sec=60" in url

    def test_http_becomes_ws(self):
        url = _build_ws_url("http://localhost:4000/api/v1", "c", ["file"], None, None)
        assert url.startswith("ws://localhost:4000/api/v1/computers/c/events")

    def test_validate_subscribe_rejects_empty(self):
        with pytest.raises(ValueError):
            _validate_subscribe([])

    def test_validate_subscribe_rejects_unknown(self):
        with pytest.raises(ValueError):
            _validate_subscribe(["bogus"])


class TestSpawnUrl:
    def test_spawn_url_has_query(self):
        url = _build_spawn_ws_url(
            "https://api.miosa.ai/api/v1",
            "comp_1",
            {"command": "vim", "rows": "24", "cols": "80"},
        )
        assert url.startswith("wss://api.miosa.ai/api/v1/computers/comp_1/exec/spawn?")
        assert "command=vim" in url
        assert "rows=24" in url
        assert "cols=80" in url


# ───────────────────────────────────────────────────────────────────────────
# Frame parsing
# ───────────────────────────────────────────────────────────────────────────


class TestFrameParsing:
    def test_parse_frame_text(self):
        frame = json.dumps(
            {
                "type": "file.created",
                "timestamp": "2026-04-01T00:00:00Z",
                "payload": {"path": "/tmp/x"},
            }
        )
        event = _parse_frame(frame)
        assert isinstance(event, ComputerEvent)
        assert event.type == "file.created"
        assert event.payload == {"path": "/tmp/x"}

    def test_parse_frame_bytes(self):
        frame = json.dumps({"type": "idle.active", "payload": {"idle_ms": 1000}}).encode()
        event = _parse_frame(frame)
        assert event is not None
        assert event.type == "idle.active"

    def test_parse_frame_bad_json_returns_none(self):
        assert _parse_frame("not json") is None
        assert _parse_frame(b"\xff\xfe") is None
        assert _parse_frame(42) is None  # type: ignore[arg-type]


# ───────────────────────────────────────────────────────────────────────────
# EventStream (fake WS)
# ───────────────────────────────────────────────────────────────────────────


class FakeWebSocket:
    """Minimal async-recv WebSocket stub."""

    def __init__(self, frames):
        self._frames = list(frames)
        self.closed = False
        self.sent: list[str] = []

    async def recv(self):
        if not self._frames:
            raise ConnectionError("closed")
        return self._frames.pop(0)

    async def send(self, data):
        self.sent.append(data)

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_event_stream_iterates_and_closes():
    frames = [
        json.dumps({"type": "file.created", "payload": {"path": "/a"}}),
        json.dumps({"type": "file.modified", "payload": {"path": "/a"}}),
    ]
    stream = EventStream(FakeWebSocket(frames))
    collected = []
    async for event in stream:
        collected.append(event)
    assert [e.type for e in collected] == ["file.created", "file.modified"]
    await stream.close()
    assert stream.is_closed


# ───────────────────────────────────────────────────────────────────────────
# ExecProcess (fake WS)
# ───────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_exec_process_resize_sends_json_frame():
    ws = FakeWebSocket([])
    proc = ExecProcess(ws)
    await proc.resize(24, 80)
    assert len(ws.sent) == 1
    sent = json.loads(ws.sent[0])
    assert sent == {"type": "resize", "rows": 24, "cols": 80}


@pytest.mark.asyncio
async def test_exec_process_write_sends_stdin_frame():
    ws = FakeWebSocket([])
    proc = ExecProcess(ws)
    await proc.write("hello\n")
    sent = json.loads(ws.sent[0])
    assert sent["type"] == "stdin"
    assert sent["data"] == "hello\n"


@pytest.mark.asyncio
async def test_exec_process_close_stdin_and_kill():
    ws = FakeWebSocket([])
    proc = ExecProcess(ws)
    await proc.close_stdin()
    assert json.loads(ws.sent[0]) == {"type": "stdin_close"}

    await proc.kill()
    # kill sends SIGKILL signal then closes
    assert any("SIGKILL" in s for s in ws.sent)
    assert ws.closed


@pytest.mark.asyncio
async def test_exec_process_wait_returns_exit_code():
    """Feed an exit frame; wait() should return its code."""
    frames = [
        json.dumps({"type": "stdout", "data": "hi\n"}),
        json.dumps({"type": "exit", "code": 7}),
    ]
    ws = FakeWebSocket(frames)
    proc = ExecProcess(ws)
    # Iterate stdout fully so the reader task processes frames.
    out: list[str] = []
    async for chunk in proc.stdout():
        out.append(chunk)
    assert out == ["hi\n"]
    code = await proc.wait()
    assert code == 7


def test_exec_process_spawn_raises_on_sync_resource(mock_api, client):
    """Verify spawn() on the sync ExecResource raises NotImplementedError.

    WebSocket connections are inherently async; spawn() is only available on
    AsyncExecResource (via AsyncMiosa).
    """
    import pytest

    from .conftest import COMPUTER_JSON

    mock_api.get("/computers/comp_abc123").respond(200, json=COMPUTER_JSON)
    comp = client.computers.get("comp_abc123")
    assert hasattr(comp.exec, "spawn")
    with pytest.raises(NotImplementedError, match="AsyncMiosa"):
        comp.exec.spawn("bash")
