"""Tests for client.webhooks — CRUD, test, deliveries, verify_signature."""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest

WEBHOOK = {
    "id": "wh_001",
    "url": "https://example.com/hook",
    "events": ["sandbox.created", "sandbox.destroyed"],
    "active": True,
    "created_at": "2026-05-26T00:00:00Z",
}


class TestWebhooks:
    def test_create(self, mock_api, client):
        route = mock_api.post("/webhooks").respond(200, json={"data": WEBHOOK})
        result = client.webhooks.create(
            url="https://example.com/hook",
            events=["sandbox.created"],
        )
        assert result["id"] == "wh_001"
        body = json.loads(route.calls.last.request.content)
        assert body["url"] == "https://example.com/hook"

    def test_list(self, mock_api, client):
        mock_api.get("/webhooks").respond(200, json={"webhooks": [WEBHOOK]})
        result = client.webhooks.list()
        assert len(result) == 1

    def test_get(self, mock_api, client):
        mock_api.get("/webhooks/wh_001").respond(200, json={"data": WEBHOOK})
        result = client.webhooks.get("wh_001")
        assert result["id"] == "wh_001"

    def test_update(self, mock_api, client):
        mock_api.patch("/webhooks/wh_001").respond(200, json={"data": {**WEBHOOK, "active": False}})
        result = client.webhooks.update("wh_001", active=False)
        assert result["active"] is False

    def test_delete(self, mock_api, client):
        route = mock_api.delete("/webhooks/wh_001").respond(204)
        client.webhooks.delete("wh_001")
        assert route.called

    def test_test_endpoint(self, mock_api, client):
        route = mock_api.post("/webhooks/wh_001/test").respond(
            200, json={"data": {"delivered": True}}
        )
        client.webhooks.test("wh_001")
        assert route.called

    def test_deliveries(self, mock_api, client):
        mock_api.get("/webhooks/wh_001/deliveries").respond(
            200,
            json={
                "deliveries": [
                    {"id": "del_001", "status": "success", "delivered_at": "2026-05-26T00:00:00Z"}
                ]
            },
        )
        result = client.webhooks.deliveries("wh_001")
        assert len(result) == 1


class TestWebhookSignature:
    def _make_header(self, body: bytes, secret: str, ts: int | None = None) -> str:
        ts = ts or int(time.time())
        signed = f"{ts}.".encode() + body
        sig = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        return f"t={ts},v1={sig}"

    def test_verify_valid(self):
        secret = "whsec_test"
        body = b'{"event":"sandbox.created"}'
        header = self._make_header(body, secret)
        assert client_verify_signature(body, header, secret) is True

    def test_verify_tampered(self):
        secret = "whsec_test"
        body = b'{"event":"sandbox.created"}'
        header = self._make_header(body, secret)
        # Tamper the body
        tampered = b'{"event":"sandbox.destroyed"}'
        assert client_verify_signature(tampered, header, secret) is False

    def test_verify_expired(self):
        secret = "whsec_test"
        body = b'{"event":"test"}'
        old_ts = int(time.time()) - 400  # older than 300s tolerance
        header = self._make_header(body, secret, ts=old_ts)
        with pytest.raises(ValueError, match="too old"):
            client_verify_signature(body, header, secret)

    def test_verify_wrong_secret(self):
        body = b'{"event":"test"}'
        header = self._make_header(body, "correct_secret")
        assert client_verify_signature(body, header, "wrong_secret") is False

    def test_verify_malformed_header(self):
        result = client_verify_signature(b"body", "not-a-valid-header", "secret")
        assert result is False

    def test_verify_current_server_signature(self):
        secret = "whsec_test"
        body = b'{"event":"run.succeeded","run_id":"run_1"}'
        digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        assert client_verify_signature(body, f"sha256={digest}", secret) is True
        assert client_verify_signature(body + b" ", f"sha256={digest}", secret) is False


def client_verify_signature(body: bytes, header: str, secret: str) -> bool:
    """Helper that calls the static method on Webhooks."""
    from miosa.resources.webhooks import Webhooks

    return Webhooks.verify_signature(body, header, secret)
