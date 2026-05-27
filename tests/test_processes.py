"""Tests for sandbox.processes.{start,list,get,stop,logs}."""

from __future__ import annotations

import json

from .conftest import SANDBOX_JSON

PROC = {
    "pid": 1234,
    "name": "dev-server",
    "command": "npm run dev",
    "status": "running",
    "started_at": "2026-05-26T00:00:00Z",
}


class TestSandboxProcesses:
    def test_start(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        route = mock_api.post("/sandboxes/sbx_abc123/processes").respond(
            200, json={"data": PROC}
        )
        sb = client.sandboxes.get("sbx_abc123")
        result = sb.processes.start("npm run dev", name="dev-server")
        assert result["pid"] == 1234
        body = json.loads(route.calls.last.request.content)
        assert body["command"] == "npm run dev"
        assert body["name"] == "dev-server"

    def test_list(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        mock_api.get("/sandboxes/sbx_abc123/processes").respond(
            200, json={"data": [PROC]}
        )
        sb = client.sandboxes.get("sbx_abc123")
        result = sb.processes.list()
        assert len(result) == 1
        assert result[0]["pid"] == 1234

    def test_get(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        mock_api.get("/sandboxes/sbx_abc123/processes/1234").respond(
            200, json={"data": PROC}
        )
        sb = client.sandboxes.get("sbx_abc123")
        result = sb.processes.get(1234)
        assert result["status"] == "running"

    def test_stop(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        route = mock_api.delete("/sandboxes/sbx_abc123/processes/1234").respond(204)
        sb = client.sandboxes.get("sbx_abc123")
        sb.processes.stop(1234)
        assert route.called

    def test_logs(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        mock_api.get("/sandboxes/sbx_abc123/processes/1234/logs").respond(
            200, json={"data": "line1\nline2\n"}
        )
        sb = client.sandboxes.get("sbx_abc123")
        result = sb.processes.logs(1234, tail=50)
        assert "line1" in result
