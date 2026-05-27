"""Tests for sandbox.preview_token()."""

from __future__ import annotations

import json

from .conftest import SANDBOX_JSON


class TestSandboxPreviewToken:
    def test_mint_token_default_params(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        route = mock_api.post("/sandboxes/sbx_abc123/preview-token").respond(
            200,
            json={
                "token": "mp_abc123",
                "url": "https://3000-sbxabc.sandbox.miosa.app?mt=mp_abc123",
                "expires_at": "2026-05-26T01:00:00Z",
                "scope": "read",
            },
        )
        sb = client.sandboxes.get("sbx_abc123")
        result = sb.preview_token()
        assert result["token"] == "mp_abc123"
        assert result["scope"] == "read"
        body = json.loads(route.calls.last.request.content)
        assert body["expires_in"] == 3600
        assert body["scope"] == "read"

    def test_mint_token_custom_params(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        route = mock_api.post("/sandboxes/sbx_abc123/preview-token").respond(
            200,
            json={
                "token": "mp_xyz",
                "url": "https://3000-sbxabc.sandbox.miosa.app?mt=mp_xyz",
                "expires_at": "2026-05-26T00:30:00Z",
                "scope": "interact",
            },
        )
        sb = client.sandboxes.get("sbx_abc123")
        result = sb.preview_token(expires_in=1800, scope="interact")
        assert result["scope"] == "interact"
        body = json.loads(route.calls.last.request.content)
        assert body["expires_in"] == 1800
        assert body["scope"] == "interact"
