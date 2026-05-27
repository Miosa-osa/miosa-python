"""Tests for sandbox.files.tree()."""

from __future__ import annotations

from .conftest import SANDBOX_JSON

TREE_RESPONSE = {
    "path": "/workspace",
    "type": "dir",
    "name": "workspace",
    "children": [
        {"path": "/workspace/app.py", "type": "file", "name": "app.py", "size": 42},
    ],
}


class TestFilesTree:
    def test_tree_default_params(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        route = mock_api.get("/sandboxes/sbx_abc123/files/tree").respond(
            200, json={"data": TREE_RESPONSE}
        )
        sb = client.sandboxes.get("sbx_abc123")
        result = sb.files.tree()
        assert result["path"] == "/workspace"
        assert result["type"] == "dir"
        assert len(result["children"]) == 1
        assert route.calls.last.request.url.params["depth"] == "3"

    def test_tree_custom_depth(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        route = mock_api.get("/sandboxes/sbx_abc123/files/tree").respond(
            200, json={"data": TREE_RESPONSE}
        )
        sb = client.sandboxes.get("sbx_abc123")
        sb.files.tree(path="/workspace/src", depth=5)
        params = route.calls.last.request.url.params
        assert params["path"] == "/workspace/src"
        assert params["depth"] == "5"
