"""Tests for MIOSA Connect SDK resources."""

from __future__ import annotations

import json

from miosa.resources.connectors import ComputerConnectors, DeploymentConnectors


def test_connectors_list_create_show_and_token(mock_api, client):
    list_route = mock_api.get(
        "/connect/connectors",
        params={
            "scope": "workspace",
            "workspace_id": "ws_123",
            "external_workspace_id": "clinic-workspace",
        },
    ).respond(200, json={"data": [{"uid": "anthropic/workspace-claude"}]})
    create_route = mock_api.post("/connect/connectors").respond(
        201, json={"data": {"uid": "anthropic/workspace-claude"}}
    )
    mock_api.get("/connect/connectors/anthropic%2Fworkspace-claude").respond(
        200, json={"data": {"uid": "anthropic/workspace-claude"}}
    )
    token_route = mock_api.post("/connect/token/github%2Facme").respond(
        200, json={"token": "provider-token", "connector": {"uid": "github/acme"}}
    )

    listed = client.connectors.list(
        scope="workspace",
        workspace_id="ws_123",
        external_workspace_id="clinic-workspace",
    )
    created = client.connectors.create(
        "anthropic",
        name="workspace-claude",
        type="api-key",
        value="sk-ant-test",
        scope="workspace",
        workspace_id="ws_123",
        external_project_id="clinic-project",
    )
    shown = client.connectors.get("anthropic/workspace-claude")
    token = client.connectors.get_token(
        "github/acme",
        subject={"type": "app"},
        installation_id="inst_123",
        project_id="prj_123",
        environment="production",
        resource_type="sandbox",
        resource_id="sbx_123",
        scopes=["repo:read"],
        external_workspace_id="clinic-workspace",
        external_user_id="clinic-user",
        external_project_id="clinic-project",
    )

    create_body = json.loads(create_route.calls.last.request.content)
    token_body = json.loads(token_route.calls.last.request.content)

    assert list_route.called
    assert listed[0]["uid"] == "anthropic/workspace-claude"
    assert created["uid"] == "anthropic/workspace-claude"
    assert shown["uid"] == "anthropic/workspace-claude"
    assert create_body == {
        "provider": "anthropic",
        "type": "api_key",
        "name": "workspace-claude",
        "uid": "anthropic/workspace-claude",
        "scope": "workspace",
        "workspace_id": "ws_123",
        "external_project_id": "clinic-project",
        "credential": {"field": "api_key", "value": "sk-ant-test"},
    }
    assert token_body == {
        "subject": {"type": "app"},
        "installation_id": "inst_123",
        "project_id": "prj_123",
        "environment": "production",
        "resource_type": "sandbox",
        "resource_id": "sbx_123",
        "scopes": ["repo:read"],
        "external_user_id": "clinic-user",
        "external_workspace_id": "clinic-workspace",
        "external_project_id": "clinic-project",
    }
    assert token["token"] == "provider-token"


def test_connectors_installations_and_project_links(mock_api, client):
    installations_route = mock_api.get(
        "/connect/installations", params={"workspace_id": "ws_123"}
    ).respond(200, json={"data": [{"id": "inst_row", "installation_id": "default"}]})
    create_link_route = mock_api.post("/connect/project-links").respond(
        201, json={"data": {"id": "link_123", "allowed_scopes": ["repo:read"]}}
    )
    links_route = mock_api.get(
        "/connect/project-links", params={"project_id": "prj_123"}
    ).respond(200, json={"data": [{"id": "link_123"}]})
    delete_route = mock_api.delete("/connect/project-links/link_123").respond(204)

    installations = client.connectors.installations(workspace_id="ws_123")
    link = client.connectors.create_project_link(
        connector="github/workspace",
        installation_id="inst_row",
        project_id="prj_123",
        environment="production",
        allowed_scopes=["repo:read"],
        mode="token-api",
        external_project_id="clinic-project",
    )
    links = client.connectors.project_links(project_id="prj_123")
    client.connectors.delete_project_link("link_123")

    create_body = json.loads(create_link_route.calls.last.request.content)

    assert installations_route.called
    assert installations[0]["installation_id"] == "default"
    assert create_body == {
        "connector": "github/workspace",
        "installation_id": "inst_row",
        "project_id": "prj_123",
        "environment": "production",
        "allowed_scopes": ["repo:read"],
        "mode": "token_api",
        "external_project_id": "clinic-project",
    }
    assert link["allowed_scopes"] == ["repo:read"]
    assert links_route.called
    assert links[0]["id"] == "link_123"
    assert delete_route.called


def test_connectors_oauth_providers_and_start(mock_api, client):
    providers_route = mock_api.get("/connect/oauth/providers").respond(
        200, json={"data": [{"provider": "github", "scopes": ["repo"]}]}
    )
    start_route = mock_api.post("/connect/oauth/start").respond(
        200,
        json={
            "data": {
                "authorize_url": "https://github.com/login/oauth/authorize",
                "state": "st_123",
            }
        },
    )

    providers = client.connectors.oauth_providers()
    started = client.connectors.start_oauth(
        "github",
        expose_as_env=True,
        owner_user_id="user_123",
        external_user_id="clinic-user",
    )

    start_body = json.loads(start_route.calls.last.request.content)

    assert providers_route.called
    assert providers[0]["provider"] == "github"
    assert start_body == {
        "provider": "github",
        "expose_as_env": True,
        "owner_user_id": "user_123",
        "external_user_id": "clinic-user",
    }
    assert started["state"] == "st_123"


def test_connectors_triggers(mock_api, client):
    create_route = mock_api.post("/connect/triggers").respond(
        201,
        json={
            "data": {
                "id": "trg_123",
                "event_types": ["app_mention"],
                "provider_adapter": "slack",
                "webhook_token": "mct_secret",
                "webhook_signing_secret": "mcs_secret",
            }
        },
    )
    list_route = mock_api.get(
        "/connect/triggers", params={"project_id": "prj_123"}
    ).respond(
        200,
        json={"data": [{"id": "trg_123", "destination_path": "/api/connect/slack"}]},
    )
    delete_route = mock_api.delete("/connect/triggers/trg_123").respond(204)

    created = client.connectors.create_trigger(
        connector="slack/workspace",
        project_id="prj_123",
        environment="production",
        destination_path="/api/connect/slack",
        event_types=["app_mention"],
        provider_adapter="slack",
        external_project_id="clinic-project",
    )
    triggers = client.connectors.triggers(project_id="prj_123")
    client.connectors.delete_trigger("trg_123")

    create_body = json.loads(create_route.calls.last.request.content)

    assert create_body == {
        "connector": "slack/workspace",
        "project_id": "prj_123",
        "environment": "production",
        "destination_path": "/api/connect/slack",
        "event_types": ["app_mention"],
        "provider_adapter": "slack",
        "external_project_id": "clinic-project",
    }
    assert created["id"] == "trg_123"
    assert created["webhook_token"] == "mct_secret"
    assert created["webhook_signing_secret"] == "mcs_secret"
    assert list_route.called
    assert triggers[0]["destination_path"] == "/api/connect/slack"
    assert delete_route.called


def test_connectors_trigger_deliveries(mock_api, client):
    deliveries_route = mock_api.get(
        "/connect/trigger-deliveries",
        params={"trigger_id": "trg_123", "event_type": "app_mention"},
    ).respond(
        200,
        json={"data": [{"id": "del_123", "state": "delivered"}]},
    )
    history_route = mock_api.get("/connect/triggers/trg_123/deliveries").respond(
        200,
        json={"data": [{"id": "del_123", "trigger_id": "trg_123"}]},
    )

    deliveries = client.connectors.trigger_deliveries(
        trigger_id="trg_123",
        event_type="app_mention",
    )
    history = client.connectors.trigger_delivery_history("trg_123")

    assert deliveries_route.called
    assert deliveries[0]["state"] == "delivered"
    assert history_route.called
    assert history[0]["trigger_id"] == "trg_123"


def test_connectors_defaults(mock_api, client):
    defaults_route = mock_api.get(
        "/connect/defaults",
        params={"project_id": "prj_123", "default_scope": "project", "target": "agent"},
    ).respond(
        200,
        json={"data": [{"id": "def_123", "default_scope": "project", "target": "agent"}]},
    )
    applicable_route = mock_api.get(
        "/connect/defaults/applicable",
        params={
            "workspace_id": "ws_123",
            "project_id": "prj_123",
            "environment": "development",
            "target": "agent",
            "resource_type": "sandbox",
            "resource_id": "sbx_123",
            "external_project_id": "clinic-project",
        },
    ).respond(
        200,
        json={
            "data": [
                {
                    "id": "def_123",
                    "default_scope": "project",
                    "target": "agent",
                    "applicability": {"matched_scope": "project"},
                }
            ]
        },
    )
    create_route = mock_api.post("/connect/defaults").respond(
        201,
        json={"data": {"id": "def_123", "default_scope": "project", "target": "agent"}},
    )
    materialize_route = mock_api.post("/connect/defaults/materialize").respond(
        200,
        json={
            "data": {
                "applied": 1,
                "results": [{"status": "applied", "default_id": "def_123"}],
            }
        },
    )
    delete_route = mock_api.delete("/connect/defaults/def_123").respond(204)

    defaults = client.connectors.defaults(
        project_id="prj_123",
        default_scope="project",
        target="agent",
    )
    applicable = client.connectors.applicable_defaults(
        workspace_id="ws_123",
        project_id="prj_123",
        environment="development",
        target="agent",
        resource_type="sandbox",
        resource_id="sbx_123",
        external_project_id="clinic-project",
    )
    created = client.connectors.create_default(
        connector="anthropic/workspace",
        project_id="prj_123",
        default_scope="project",
        target="agent",
        allowed_scopes=["messages:create"],
        mode="brokered-env",
        external_project_id="clinic-project",
    )
    materialized = client.connectors.materialize_defaults(
        workspace_id="ws_123",
        project_id="prj_123",
        environment="development",
        target="agent",
        resource_type="sandbox",
        resource_id="sbx_123",
        external_project_id="clinic-project",
    )
    client.connectors.delete_default("def_123")

    create_body = json.loads(create_route.calls.last.request.content)
    materialize_body = json.loads(materialize_route.calls.last.request.content)

    assert defaults_route.called
    assert applicable_route.called
    assert defaults[0]["target"] == "agent"
    assert applicable[0]["applicability"]["matched_scope"] == "project"
    assert create_body == {
        "connector": "anthropic/workspace",
        "project_id": "prj_123",
        "allowed_scopes": ["messages:create"],
        "mode": "brokered_env",
        "default_scope": "project",
        "target": "agent",
        "external_project_id": "clinic-project",
    }
    assert materialize_body == {
        "workspace_id": "ws_123",
        "project_id": "prj_123",
        "environment": "development",
        "target": "agent",
        "resource_type": "sandbox",
        "resource_id": "sbx_123",
        "external_project_id": "clinic-project",
    }
    assert created["default_scope"] == "project"
    assert materialized["applied"] == 1
    assert delete_route.called


def test_sandbox_connector_bindings(mock_api, client):
    mock_api.get("/sandboxes/sbx_abc123").respond(
        200,
        json={
            "data": {
                "id": "sbx_abc123",
                "state": "running",
                "ready": True,
            }
        },
    )
    list_route = mock_api.get("/sandboxes/sbx_abc123/connectors").respond(
        200, json={"data": [{"id": "bnd_123"}]}
    )
    attach_route = mock_api.post("/sandboxes/sbx_abc123/connectors").respond(
        201, json={"data": {"id": "bnd_123", "expose_as_env": "ANTHROPIC_API_KEY"}}
    )
    sync_route = mock_api.post("/sandboxes/sbx_abc123/connectors/sync").respond(
        200, json={"data": {"synced": True}}
    )
    preflight_route = mock_api.post(
        "/sandboxes/sbx_abc123/connectors/preflight"
    ).respond(200, json={"data": {"status": {"bound": True}}})
    detach_route = mock_api.delete(
        "/sandboxes/sbx_abc123/connectors/anthropic%2Fworkspace-claude"
    ).respond(204)

    sandbox = client.sandboxes.get("sbx_abc123")
    listed = sandbox.connectors.list()
    binding = sandbox.connectors.attach(
        "anthropic/workspace-claude",
        env="ANTHROPIC_API_KEY",
        mode="brokered-env",
        external_workspace_id="clinic-workspace",
    )
    sync = sandbox.connectors.sync()
    preflight = sandbox.connectors.preflight(connector="anthropic/workspace-claude")
    sandbox.connectors.detach("anthropic/workspace-claude")

    attach_body = json.loads(attach_route.calls.last.request.content)
    preflight_body = json.loads(preflight_route.calls.last.request.content)

    assert list_route.called
    assert listed[0]["id"] == "bnd_123"
    assert binding["id"] == "bnd_123"
    assert attach_body == {
        "connector": "anthropic/workspace-claude",
        "env_name": "ANTHROPIC_API_KEY",
        "mode": "brokered_env",
        "external_workspace_id": "clinic-workspace",
    }
    assert sync_route.called
    assert sync["synced"] is True
    assert preflight_body == {"connector": "anthropic/workspace-claude"}
    assert preflight["status"]["bound"] is True
    assert detach_route.called


def test_computer_connector_bindings(mock_api, client):
    list_route = mock_api.get("/computers/cmp_abc123/connectors").respond(
        200, json={"data": [{"id": "bnd_123"}]}
    )
    attach_route = mock_api.post("/computers/cmp_abc123/connectors").respond(
        201, json={"data": {"id": "bnd_123", "expose_as_env": "ANTHROPIC_API_KEY"}}
    )
    sync_route = mock_api.post("/computers/cmp_abc123/connectors/sync").respond(
        200, json={"data": {"status": "materialized"}}
    )
    preflight_route = mock_api.post(
        "/computers/cmp_abc123/connectors/preflight"
    ).respond(200, json={"data": {"status": {"bound": True}}})
    detach_route = mock_api.delete(
        "/computers/cmp_abc123/connectors/anthropic%2Fcomputer"
    ).respond(204)

    connectors = ComputerConnectors(client._transport, "cmp_abc123")
    listed = connectors.list()
    binding = connectors.attach(
        "anthropic/computer",
        env="ANTHROPIC_API_KEY",
        mode="brokered-env",
    )
    sync = connectors.sync()
    preflight = connectors.preflight(connector="anthropic/computer")
    connectors.detach("anthropic/computer")

    attach_body = json.loads(attach_route.calls.last.request.content)
    preflight_body = json.loads(preflight_route.calls.last.request.content)

    assert list_route.called
    assert listed[0]["id"] == "bnd_123"
    assert binding["expose_as_env"] == "ANTHROPIC_API_KEY"
    assert attach_body == {
        "connector": "anthropic/computer",
        "env_name": "ANTHROPIC_API_KEY",
        "mode": "brokered_env",
    }
    assert sync_route.called
    assert sync["status"] == "materialized"
    assert preflight_body == {"connector": "anthropic/computer"}
    assert preflight["status"]["bound"] is True
    assert detach_route.called


def test_deployment_connector_bindings(mock_api, client):
    list_route = mock_api.get("/deployments/dep_abc123/connectors").respond(
        200, json={"data": [{"id": "bnd_123"}]}
    )
    attach_route = mock_api.post("/deployments/dep_abc123/connectors").respond(
        201,
        json={
            "data": {
                "id": "bnd_123",
                "expose_as_env": "ANTHROPIC_API_KEY",
                "sync": {"requires_redeploy": True},
            }
        },
    )
    sync_route = mock_api.post("/deployments/dep_abc123/connectors/sync").respond(
        200, json={"data": {"status": "materialized_on_next_boot"}}
    )
    preflight_route = mock_api.post(
        "/deployments/dep_abc123/connectors/preflight"
    ).respond(200, json={"data": {"status": {"bound": True}}})
    detach_route = mock_api.delete(
        "/deployments/dep_abc123/connectors/anthropic%2Fdeployment"
    ).respond(204)

    connectors = DeploymentConnectors(client._transport, "dep_abc123")
    listed = connectors.list()
    binding = connectors.attach(
        "anthropic/deployment",
        env="ANTHROPIC_API_KEY",
        mode="brokered-env",
    )
    sync = connectors.sync()
    preflight = connectors.preflight(connector="anthropic/deployment")
    connectors.detach("anthropic/deployment")

    attach_body = json.loads(attach_route.calls.last.request.content)
    preflight_body = json.loads(preflight_route.calls.last.request.content)

    assert list_route.called
    assert listed[0]["id"] == "bnd_123"
    assert binding["sync"]["requires_redeploy"] is True
    assert attach_body == {
        "connector": "anthropic/deployment",
        "env_name": "ANTHROPIC_API_KEY",
        "mode": "brokered_env",
    }
    assert sync_route.called
    assert sync["status"] == "materialized_on_next_boot"
    assert preflight_body == {"connector": "anthropic/deployment"}
    assert preflight["status"]["bound"] is True
    assert detach_route.called
