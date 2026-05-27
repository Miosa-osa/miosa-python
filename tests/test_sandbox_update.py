"""Tests for sandbox.update()."""

from __future__ import annotations

import json

from .conftest import SANDBOX_JSON


class TestSandboxUpdate:
    def test_patch_name_and_slug(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        route = mock_api.patch("/sandboxes/sbx_abc123").respond(
            200, json={"data": {**SANDBOX_JSON, "name": "new-name", "slug": "new-slug"}}
        )
        sb = client.sandboxes.get("sbx_abc123")
        sb.update(name="new-name", slug="new-slug")
        body = json.loads(route.calls.last.request.content)
        assert body["name"] == "new-name"
        assert body["slug"] == "new-slug"

    def test_patch_metadata(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        route = mock_api.patch("/sandboxes/sbx_abc123").respond(
            200, json={"data": {**SANDBOX_JSON, "metadata": {"foo": "bar"}}}
        )
        sb = client.sandboxes.get("sbx_abc123")
        sb.update(metadata={"foo": "bar"})
        body = json.loads(route.calls.last.request.content)
        assert body["metadata"] == {"foo": "bar"}

    def test_patch_omits_none_values(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        route = mock_api.patch("/sandboxes/sbx_abc123").respond(
            200, json={"data": SANDBOX_JSON}
        )
        sb = client.sandboxes.get("sbx_abc123")
        sb.update(always_on=True)
        body = json.loads(route.calls.last.request.content)
        assert "name" not in body
        assert body["always_on"] is True
