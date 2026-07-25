"""Docker Deploy host resource tests."""

from __future__ import annotations

import json


HOST_JSON = {
    "id": "ddh_123",
    "tenant_id": "ten_123",
    "workspace_id": "ws_123",
    "external_workspace_id": "dr-smith",
    "computer_id": "comp_123",
    "fleet_node_id": None,
    "status": "bootstrapping",
    "size": "medium",
    "region": "us",
    "portal_domain": "dr-smith.deploy.miosa.ai",
    "runtime_base_url": "http://10.0.0.12:3000",
    "agent_base_url": "http://10.0.0.12:8090",
    "appliance_image": "registry.miosa.ai/miosa/docker-deploy-appliance:latest",
    "appliance_version": "latest",
    "appliance_status": "starting",
    "agent_last_seen_at": None,
    "metadata": {},
    "created_at": "2026-06-09T00:00:00Z",
    "updated_at": "2026-06-09T00:00:00Z",
}


def test_list_docker_deploy_hosts(mock_api, client):
    route = mock_api.get("/docker-deploy/hosts").respond(
        200, json={"data": [HOST_JSON]}
    )

    hosts = client.docker_deploy.list_hosts(workspace_id="ws_123")

    assert route.calls.last.request.url.params["workspace_id"] == "ws_123"
    assert hosts[0].id == "ddh_123"
    assert hosts[0].status == "bootstrapping"
    assert hosts[0].appliance_status == "starting"


def test_ensure_docker_deploy_host(mock_api, client):
    route = mock_api.post("/docker-deploy/hosts/ensure").respond(
        201, json={"host": HOST_JSON, "queued": True}
    )

    host = client.docker_deploy.ensure_host(workspace_id="ws_123")

    payload = json.loads(route.calls.last.request.content)
    assert payload == {"workspace_id": "ws_123"}
    assert host.id == "ddh_123"
    assert host.workspace_id == "ws_123"


def test_list_docker_deploy_templates(mock_api, client):
    mock_api.get("/docker-deploy/templates").respond(
        200,
        json={"data": [{"id": "nextjs-app", "name": "Next.js app"}]},
    )

    templates = client.docker_deploy.list_templates()

    assert templates[0].id == "nextjs-app"
    assert templates[0].name == "Next.js app"


def test_get_docker_deploy_template(mock_api, client):
    mock_api.get("/docker-deploy/templates/compose-full-stack").respond(
        200,
        json={"template": {"id": "compose-full-stack", "name": "Compose full stack"}},
    )

    template = client.docker_deploy.get_template("compose-full-stack")

    assert template.id == "compose-full-stack"
