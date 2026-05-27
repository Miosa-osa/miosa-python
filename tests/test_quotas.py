"""Tests for client.quotas.{get,set,delete}."""

from __future__ import annotations

import json

QUOTA = {
    "external_user_id": "usr_123",
    "max_sandboxes": 5,
    "max_concurrent": 2,
    "max_storage_gb": 10,
    "max_credit_cents": 5000,
    "usage": {"sandboxes": 2, "concurrent": 1},
}


class TestQuotas:
    def test_get(self, mock_api, client):
        route = mock_api.get("/quotas/external/usr_123").respond(
            200, json={"data": QUOTA}
        )
        result = client.quotas.get("usr_123")
        assert result["external_user_id"] == "usr_123"
        assert result["max_sandboxes"] == 5
        assert route.called

    def test_set(self, mock_api, client):
        route = mock_api.put("/quotas/external/usr_123").respond(
            200, json={"data": {**QUOTA, "max_sandboxes": 10}}
        )
        result = client.quotas.set("usr_123", max_sandboxes=10)
        assert result["max_sandboxes"] == 10
        body = json.loads(route.calls.last.request.content)
        assert body["max_sandboxes"] == 10
        assert "max_concurrent" not in body

    def test_set_multiple_fields(self, mock_api, client):
        route = mock_api.put("/quotas/external/usr_123").respond(
            200, json={"data": QUOTA}
        )
        client.quotas.set("usr_123", max_sandboxes=5, max_concurrent=2, max_credit_cents=5000)
        body = json.loads(route.calls.last.request.content)
        assert body["max_sandboxes"] == 5
        assert body["max_concurrent"] == 2
        assert body["max_credit_cents"] == 5000

    def test_delete(self, mock_api, client):
        route = mock_api.delete("/quotas/external/usr_123").respond(204)
        client.quotas.delete("usr_123")
        assert route.called
