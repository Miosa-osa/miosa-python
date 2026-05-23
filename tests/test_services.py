"""Tests for the Services resource."""

from __future__ import annotations

import json

from miosa.types import ServiceData, ServiceStatus

from .conftest import COMPUTER_JSON

SERVICE_JSON = {
    "id": "svc_001",
    "computer_id": "comp_abc123",
    "name": "web",
    "command": "python -m http.server 8000",
    "status": "running",
    "working_dir": "/workspace",
    "env": {"PORT": "8000"},
    "restart_policy": "on-failure",
    "port": 8000,
    "pid": 42,
    "exit_code": None,
    "created_at": "2026-04-01T00:00:00Z",
    "updated_at": "2026-04-01T00:00:00Z",
}


def _get_computer(mock_api, client):
    mock_api.get("/computers/comp_abc123").respond(200, json=COMPUTER_JSON)
    return client.computers.get("comp_abc123")


class TestServices:
    def test_create_sends_name_command_port(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        route = mock_api.post("/computers/comp_abc123/services").respond(
            200, json={"data": SERVICE_JSON}
        )
        svc = comp.services.create(
            "web",
            "python -m http.server 8000",
            working_dir="/workspace",
            port=8000,
        )
        assert isinstance(svc, ServiceData)
        assert svc.id == "svc_001"
        assert svc.status == ServiceStatus.RUNNING

        body = json.loads(route.calls.last.request.content)
        assert body["name"] == "web"
        assert body["command"] == "python -m http.server 8000"
        assert body["working_dir"] == "/workspace"
        assert body["port"] == 8000

    def test_list(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        mock_api.get("/computers/comp_abc123/services").respond(
            200, json={"data": [SERVICE_JSON]}
        )
        services = comp.services.list()
        assert len(services) == 1
        assert services[0].name == "web"

    def test_get(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        mock_api.get("/computers/comp_abc123/services/svc_001").respond(
            200, json={"data": SERVICE_JSON}
        )
        svc = comp.services.get("svc_001")
        assert svc.id == "svc_001"

    def test_start_stop_restart(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        started = {**SERVICE_JSON, "status": "running"}
        stopped = {**SERVICE_JSON, "status": "stopped"}
        mock_api.post("/computers/comp_abc123/services/svc_001/start").respond(
            200, json={"data": started}
        )
        mock_api.post("/computers/comp_abc123/services/svc_001/stop").respond(
            200, json={"data": stopped}
        )
        mock_api.post(
            "/computers/comp_abc123/services/svc_001/restart"
        ).respond(200, json={"data": started})

        assert comp.services.start("svc_001").status == ServiceStatus.RUNNING
        assert comp.services.stop("svc_001").status == ServiceStatus.STOPPED
        assert comp.services.restart("svc_001").status == ServiceStatus.RUNNING

    def test_delete(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        route = mock_api.delete(
            "/computers/comp_abc123/services/svc_001"
        ).respond(200, json={})
        comp.services.delete("svc_001")
        assert route.called
