"""Tests for client.audit_log.list()."""

from __future__ import annotations

EVENTS = [
    {
        "id": "evt_001",
        "type": "sandbox.created",
        "actor": {"type": "user", "id": "usr_123"},
        "resource": {"type": "sandbox", "id": "sbx_abc"},
        "ts": "2026-05-26T00:00:00Z",
        "metadata": {},
    }
]


class TestAuditLog:
    def test_list_no_filters(self, mock_api, client):
        route = mock_api.get("/audit-log").respond(200, json={"data": EVENTS})
        result = client.audit_log.list()
        assert len(result) == 1
        assert result[0]["type"] == "sandbox.created"
        assert route.called

    def test_list_with_type_filter(self, mock_api, client):
        route = mock_api.get("/audit-log").respond(200, json={"data": EVENTS})
        client.audit_log.list(type="sandbox.created")
        params = route.calls.last.request.url.params
        assert params["type"] == "sandbox.created"

    def test_list_with_actor_id(self, mock_api, client):
        route = mock_api.get("/audit-log").respond(200, json={"data": EVENTS})
        client.audit_log.list(actor_id="usr_123", limit=50)
        params = route.calls.last.request.url.params
        assert params["actor_id"] == "usr_123"
        assert params["limit"] == "50"

    def test_list_with_cursor(self, mock_api, client):
        route = mock_api.get("/audit-log").respond(200, json={"data": EVENTS})
        client.audit_log.list(after="cursor_xyz")
        params = route.calls.last.request.url.params
        assert params["after"] == "cursor_xyz"

    def test_list_with_resource_filters(self, mock_api, client):
        route = mock_api.get("/audit-log").respond(200, json={"data": EVENTS})
        client.audit_log.list(resource_type="sandbox", resource_id="sbx_abc")
        params = route.calls.last.request.url.params
        assert params["resource_type"] == "sandbox"
        assert params["resource_id"] == "sbx_abc"
