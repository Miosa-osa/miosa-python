"""Tests for sandbox.files.write_many()."""

from __future__ import annotations

import base64
import json

from .conftest import SANDBOX_JSON

WRITE_MANY_RESPONSE = {
    "written": [
        {"path": "/workspace/a.py", "size_bytes": 10},
        {"path": "/workspace/b.py", "size_bytes": 5},
    ],
    "failed": [],
}


class TestFilesWriteMany:
    def test_write_many_encodes_content(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        route = mock_api.post("/sandboxes/sbx_abc123/files/write-many").respond(
            200, json={"data": WRITE_MANY_RESPONSE}
        )
        sb = client.sandboxes.get("sbx_abc123")
        result = sb.files.write_many([
            {"path": "/workspace/a.py", "content": "print(1)"},
            {"path": "/workspace/b.py", "content": b"# hi"},
        ])
        assert result["written"][0]["path"] == "/workspace/a.py"
        body = json.loads(route.calls.last.request.content)
        files = body["files"]
        assert len(files) == 2
        # Verify base64 encoding
        decoded = base64.b64decode(files[0]["content_base64"]).decode()
        assert decoded == "print(1)"
        assert "content_base64" in files[0]

    def test_write_many_returns_written_failed(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        mock_api.post("/sandboxes/sbx_abc123/files/write-many").respond(
            200,
            json={
                "data": {
                    "written": [{"path": "/workspace/ok.py", "size_bytes": 3}],
                    "failed": [{"path": "/workspace/bad.py", "error": "permission denied"}],
                }
            },
        )
        sb = client.sandboxes.get("sbx_abc123")
        result = sb.files.write_many([
            {"path": "/workspace/ok.py", "content": "ok"},
            {"path": "/workspace/bad.py", "content": "bad"},
        ])
        assert len(result["written"]) == 1
        assert len(result["failed"]) == 1
