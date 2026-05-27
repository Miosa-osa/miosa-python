"""Tests for sandbox.share.{create,list,revoke}."""

from __future__ import annotations

import json

from .conftest import SANDBOX_JSON

SHARE = {
    "share_id": "share_abc",
    "share_url": "https://3000-sbxabc.sandbox.miosa.app?ms=token123",
    "expires_at": "2026-05-26T01:00:00Z",
    "scope": "read",
}


class TestSandboxShare:
    def test_create(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        route = mock_api.post("/sandboxes/sbx_abc123/shares").respond(
            200, json={"data": SHARE}
        )
        sb = client.sandboxes.get("sbx_abc123")
        result = sb.share.create(expires_in=3600, scope="read")
        assert result["share_id"] == "share_abc"
        assert "share_url" in result
        body = json.loads(route.calls.last.request.content)
        assert body["expires_in"] == 3600
        assert body["scope"] == "read"

    def test_create_no_expiry(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        route = mock_api.post("/sandboxes/sbx_abc123/shares").respond(
            200, json={"data": SHARE}
        )
        sb = client.sandboxes.get("sbx_abc123")
        sb.share.create()
        body = json.loads(route.calls.last.request.content)
        assert "expires_in" not in body
        assert body["scope"] == "read"

    def test_list(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        mock_api.get("/sandboxes/sbx_abc123/shares").respond(
            200, json={"data": [SHARE]}
        )
        sb = client.sandboxes.get("sbx_abc123")
        result = sb.share.list()
        assert len(result) == 1
        assert result[0]["share_id"] == "share_abc"

    def test_revoke(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        route = mock_api.delete("/sandboxes/sbx_abc123/shares/share_abc").respond(204)
        sb = client.sandboxes.get("sbx_abc123")
        sb.share.revoke("share_abc")
        assert route.called
