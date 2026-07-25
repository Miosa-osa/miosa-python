"""Deployment resource tests."""

from __future__ import annotations

import json

DEPLOYMENT_JSON = {
    "id": "dep_123",
    "tenant_id": "ten_123",
    "owner_id": "usr_123",
    "workspace_id": "ws_123",
    "project_id": "prj_123",
    "name": "Clinic Intake",
    "slug": "clinic-intake",
    "repo_url": "https://github.com/clinic-iq/intake",
    "repo_provider": "github",
    "branch": "main",
    "build_command": None,
    "run_command": None,
    "runtime_image": None,
    "current_build_id": None,
    "active_version_id": None,
    "state": "pending",
    "auto_deploy": True,
    "custom_domain_id": None,
    "linked_database_id": None,
    "deployment_product": "docker_deploy",
    "docker_deploy_host_id": "ddh_123",
    "metadata": {"deployment_product": "docker_deploy", "client": "clinic-iq"},
    "external_workspace_id": "dr-smith",
    "external_user_id": None,
    "external_project_id": "lead-magnet",
    "public_url": None,
    "auto_subdomain": "https://clinic-intake.panther.miosa.app",
    "created_at": "2026-06-09T00:00:00Z",
    "updated_at": "2026-06-09T00:00:00Z",
}


def test_create_docker_deploy_marks_deployment(mock_api, client):
    route = mock_api.post("/deployments").respond(
        200, json={"data": DEPLOYMENT_JSON}
    )

    deployment = client.deployments.create_docker_deploy(
        name="Clinic Intake",
        repo_url="https://github.com/clinic-iq/intake",
        external_workspace_id="dr-smith",
        external_project_id="lead-magnet",
        metadata={"client": "clinic-iq"},
        idempotency_key="idem-123",
    )

    payload = json.loads(route.calls.last.request.content)
    assert payload["metadata"] == {
        "client": "clinic-iq",
        "deployment_product": "docker_deploy",
    }
    assert payload["external_workspace_id"] == "dr-smith"
    assert payload["external_project_id"] == "lead-magnet"
    assert route.calls.last.request.headers["idempotency-key"] == "idem-123"
    assert deployment.deployment_product == "docker_deploy"
    assert deployment.docker_deploy_host_id == "ddh_123"
    assert deployment.workspace_id == "ws_123"
    assert deployment.auto_subdomain == "https://clinic-intake.panther.miosa.app"


def test_prove_docker_deploy_uses_app_truth(mock_api, client):
    deployment = {
        **DEPLOYMENT_JSON,
        "state": "running",
        "public_url": "https://clinic.example.com",
        "docker_deploy_app": {
            "app_id": "dokploy_app_123",
            "container_id": "container_123",
            "status": "running",
            "runtime_ip": "172.16.0.2",
            "runtime_port": 24001,
            "public_url": "https://clinic.example.com",
        },
    }
    mock_api.get("/deployments/dep_123").respond(200, json={"data": deployment})
    mock_api.get("/docker-deploy/hosts/ddh_123").respond(
        200,
        json={
            "data": {
                "id": "ddh_123",
                "status": "active",
                "appliance_status": "healthy",
            }
        },
    )

    proof = client.deployments.prove("dep_123")

    assert proof["ok"] is True
    assert {
        "id": "docker_deploy_app_row",
        "ok": True,
        "message": "App Engine app status=running.",
        "details": {
            "app_id": "dokploy_app_123",
            "container_id": "container_123",
            "status": "running",
        },
        "recovery": ["Publish through App Engine again."],
    } in proof["checks"]


def test_prove_docker_deploy_fails_metadata_only(mock_api, client):
    deployment = {
        **DEPLOYMENT_JSON,
        "state": "running",
        "public_url": "https://clinic.example.com",
        "docker_deploy_app": None,
        "metadata": {
            "deployment_product": "docker_deploy",
            "runtime": {"ip": "172.16.0.1", "port": 20000},
        },
    }
    mock_api.get("/deployments/dep_123").respond(200, json={"data": deployment})
    mock_api.get("/docker-deploy/hosts/ddh_123").respond(
        200,
        json={
            "data": {
                "id": "ddh_123",
                "status": "active",
                "appliance_status": "healthy",
            }
        },
    )

    proof = client.deployments.prove("dep_123")

    assert proof["ok"] is False
    checks = {check["id"]: check for check in proof["checks"]}
    assert checks["docker_deploy_app_row"]["ok"] is False
    assert checks["docker_deploy_container_route"]["ok"] is False
    assert proof["next_actions"]


def test_promote_release_generates_a_deterministic_idempotency_key(mock_api, client):
    route = mock_api.post("/deployments/dep_123/releases/rel_456/promote").respond(
        200, json={"data": DEPLOYMENT_JSON}
    )

    client.deployments.releases("dep_123").promote("rel_456")

    assert (
        route.calls.last.request.headers["idempotency-key"]
        == "promote:dep_123:rel_456"
    )
