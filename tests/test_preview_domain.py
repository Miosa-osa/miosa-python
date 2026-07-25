"""Tests for client.tenant.preview_domain."""

from __future__ import annotations

import json


class TestPreviewDomain:
    def test_get(self, mock_api, client):
        route = mock_api.get("/tenant/preview-domain").respond(
            200, json={"data": {"domain": "preview.example.com", "verified_at": None}}
        )
        result = client.tenant.preview_domain.get()
        assert result["domain"] == "preview.example.com"
        assert route.called

    def test_set(self, mock_api, client):
        route = mock_api.put("/tenant/preview-domain").respond(
            200, json={"data": {"domain": "new.example.com", "verified_at": None}}
        )
        result = client.tenant.preview_domain.set("new.example.com")
        assert result["domain"] == "new.example.com"
        body = json.loads(route.calls.last.request.content)
        assert body == {"preview_domain": "new.example.com"}

    def test_verify(self, mock_api, client):
        route = mock_api.post("/tenant/preview-domain/verify").respond(
            200, json={"data": {"verified": True, "target": "proxy.miosa.app"}}
        )
        result = client.tenant.preview_domain.verify()
        assert result["verified"] is True
        assert route.called

    def test_delete(self, mock_api, client):
        route = mock_api.delete("/tenant/preview-domain").respond(204)
        client.tenant.preview_domain.delete()
        assert route.called
