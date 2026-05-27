"""Tests for client.events.stream() — tenant SSE stream."""

from __future__ import annotations

import json

import httpx
import respx

from miosa import Miosa
from .conftest import API_KEY, BASE_URL


def _make_sse_response(events: list[dict]) -> bytes:
    """Build a minimal SSE byte stream from a list of event dicts."""
    lines = []
    for evt in events:
        if "event" in evt:
            lines.append(f"event: {evt['event']}")
        lines.append(f"data: {json.dumps(evt.get('data', {}))}")
        lines.append("")  # blank line = event separator
    return "\n".join(lines).encode()


class TestTenantEventsStream:
    def test_stream_calls_correct_endpoint(self, mock_api, client):
        sse_body = _make_sse_response([
            {"event": "sandbox.created", "data": {"id": "sbx_1"}},
        ])
        route = mock_api.get("/events/stream").respond(
            200,
            content=sse_body,
            headers={"content-type": "text/event-stream"},
        )
        events = list(client.events.stream(types=["sandbox.*"]))
        params = route.calls.last.request.url.params
        assert params["types"] == "sandbox.*"

    def test_stream_no_types_filter(self, mock_api, client):
        sse_body = _make_sse_response([])
        route = mock_api.get("/events/stream").respond(
            200,
            content=sse_body,
            headers={"content-type": "text/event-stream"},
        )
        list(client.events.stream())
        params = route.calls.last.request.url.params
        assert "types" not in params

    def test_stream_yields_parsed_events(self, mock_api, client):
        sse_body = _make_sse_response([
            {"event": "sandbox.created", "data": {"id": "sbx_1", "state": "running"}},
            {"event": "sandbox.destroyed", "data": {"id": "sbx_2"}},
        ])
        mock_api.get("/events/stream").respond(
            200,
            content=sse_body,
            headers={"content-type": "text/event-stream"},
        )
        events = list(client.events.stream())
        # Each event should be a dict with _event_type set
        assert all(isinstance(e, dict) for e in events)
