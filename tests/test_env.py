"""Tests for sandbox.env.{get,set,delete}."""

from __future__ import annotations

import json

from .conftest import SANDBOX_JSON

ENV_LIST = [
    {"key": "DEBUG", "encrypted": False, "value": "1"},
    {"key": "SECRET", "encrypted": True},
]


class TestSandboxEnv:
    def test_get(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        route = mock_api.get("/sandboxes/sbx_abc123/env").respond(
            200, json={"data": ENV_LIST}
        )
        sb = client.sandboxes.get("sbx_abc123")
        result = sb.env.get()
        assert result == ENV_LIST
        assert route.called

    def test_list_alias(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        mock_api.get("/sandboxes/sbx_abc123/env").respond(200, json={"data": ENV_LIST})
        sb = client.sandboxes.get("sbx_abc123")
        result = sb.env.list()
        assert result == ENV_LIST

    def test_set(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        route = mock_api.put("/sandboxes/sbx_abc123/env").respond(
            200, json={"data": {"updated": True}}
        )
        sb = client.sandboxes.get("sbx_abc123")
        sb.env.set([{"key": "FOO", "value": "bar"}])
        body = json.loads(route.calls.last.request.content)
        assert body == {"vars": [{"key": "FOO", "value": "bar"}]}

    def test_delete(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        route = mock_api.delete("/sandboxes/sbx_abc123/env/DEBUG").respond(204)
        sb = client.sandboxes.get("sbx_abc123")
        sb.env.delete("DEBUG")
        assert route.called
