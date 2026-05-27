"""Tests for client.usage.get()."""

from __future__ import annotations

USAGE_RESPONSE = {
    "period_start": "2026-05-01T00:00:00Z",
    "period_end": "2026-05-31T23:59:59Z",
    "results": [
        {
            "external_user_id": "usr_123",
            "sandbox_seconds": 3600,
            "computer_seconds": 0,
            "storage_gb_hours": 0.5,
            "credit_cents": 25,
        }
    ],
}


class TestUsageGet:
    def test_get_with_external_user_id(self, mock_api, client):
        route = mock_api.get("/usage").respond(200, json={"data": USAGE_RESPONSE})
        result = client.usage.get(external_user_id="usr_123", period="30d")
        assert "results" in result
        assert result["results"][0]["external_user_id"] == "usr_123"
        params = route.calls.last.request.url.params
        assert params["external_user_id"] == "usr_123"
        assert params["period"] == "30d"

    def test_get_group_by(self, mock_api, client):
        route = mock_api.get("/usage").respond(200, json={"data": USAGE_RESPONSE})
        client.usage.get(group_by="external_user_id", period="7d")
        params = route.calls.last.request.url.params
        assert params["group_by"] == "external_user_id"

    def test_get_with_start_end(self, mock_api, client):
        route = mock_api.get("/usage").respond(200, json={"data": USAGE_RESPONSE})
        client.usage.get(start="2026-05-01T00:00:00Z", end="2026-05-31T23:59:59Z")
        params = route.calls.last.request.url.params
        assert "start" in params
        assert "end" in params

    def test_get_no_filters(self, mock_api, client):
        route = mock_api.get("/usage").respond(200, json={"data": USAGE_RESPONSE})
        result = client.usage.get()
        assert route.called
