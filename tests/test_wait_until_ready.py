"""Tests for the streaming Sandbox.wait_until_ready helper."""

from __future__ import annotations

import httpx
import pytest
import respx

from miosa import Miosa

from .conftest import API_KEY, BASE_URL, SANDBOX_JSON


def _sandbox(client: Miosa):
    """Build a Sandbox handle without round-tripping create()."""
    return client.sandboxes._transport, dict(SANDBOX_JSON)


@pytest.fixture
def client():
    c = Miosa(api_key=API_KEY, base_url=BASE_URL, max_retries=0)
    yield c
    c.close()


class TestWaitUntilReady:
    def test_stream_returns_true_on_ready_event(self, client):
        from miosa.resources.sandboxes import Sandbox

        sse_body = (
            b": keepalive\n\n"
            b"event: ready\n"
            b'data: {"ready_at":"2026-05-18T00:00:00Z"}\n\n'
        )
        with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
            router.get(f"/sandboxes/{SANDBOX_JSON['id']}/readiness/stream").mock(
                return_value=httpx.Response(200, content=sse_body, headers={"content-type": "text/event-stream"})
            )

            sandbox = Sandbox(client._transport, dict(SANDBOX_JSON))
            assert sandbox.wait_until_ready(timeout=5.0) is True

    def test_stream_returns_false_on_timeout_event(self, client):
        from miosa.resources.sandboxes import Sandbox

        sse_body = (
            b": keepalive\n\n"
            b"event: timeout\n"
            b'data: {"reason":"not_ready_after_30s"}\n\n'
        )
        with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
            router.get(f"/sandboxes/{SANDBOX_JSON['id']}/readiness/stream").mock(
                return_value=httpx.Response(200, content=sse_body, headers={"content-type": "text/event-stream"})
            )

            sandbox = Sandbox(client._transport, dict(SANDBOX_JSON))
            assert sandbox.wait_until_ready(timeout=5.0) is False

    def test_stream_404_falls_back_to_polling_and_returns_true(self, client):
        from miosa.resources.sandboxes import Sandbox

        with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
            router.get(f"/sandboxes/{SANDBOX_JSON['id']}/readiness/stream").mock(
                return_value=httpx.Response(404, json={"error": "no such endpoint"})
            )
            # polling fallback hits /readiness — first call returns ready=False,
            # second returns ready=True so we exercise the loop at least once.
            poll = router.get(f"/sandboxes/{SANDBOX_JSON['id']}/readiness")
            poll.side_effect = [
                httpx.Response(200, json={"data": {"ready": False}}),
                httpx.Response(200, json={"data": {"ready": True}}),
            ]

            sandbox = Sandbox(client._transport, dict(SANDBOX_JSON))
            assert sandbox.wait_until_ready(timeout=2.0) is True

    def test_stream_false_default_uses_polling_only(self, client):
        """stream=False must NOT call the SSE endpoint."""
        from miosa.resources.sandboxes import Sandbox

        with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
            stream_route = router.get(
                f"/sandboxes/{SANDBOX_JSON['id']}/readiness/stream"
            )
            poll = router.get(f"/sandboxes/{SANDBOX_JSON['id']}/readiness").mock(
                return_value=httpx.Response(200, json={"data": {"ready": True}})
            )

            sandbox = Sandbox(client._transport, dict(SANDBOX_JSON))
            assert sandbox.wait_until_ready(timeout=2.0, stream=False) is True
            assert stream_route.called is False
            assert poll.called is True
