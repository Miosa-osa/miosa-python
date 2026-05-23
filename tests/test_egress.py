"""Tests for the Egress (security) namespaces — secrets, network, audit."""

from __future__ import annotations

import json

import pytest

from miosa.resources.egress_secrets import OauthFlow

from .conftest import SANDBOX_JSON


# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _get_sandbox(mock_api, client):
    mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
    return client.sandboxes.get("sbx_abc123")


SECRET_JSON = {
    "id": "sec_abc",
    "name": "OPENAI_API_KEY",
    "type": "api_key",
    "scope": "user",
    "masked_value": "sk-...abc",
    "created_at": "2026-05-21T00:00:00Z",
}


# ─── client.secrets ──────────────────────────────────────────────────────────


class TestEgressSecrets:
    def test_set_posts_to_egress_secrets(self, mock_api, client):
        route = mock_api.post("/egress/secrets").respond(
            201, json={"data": SECRET_JSON}
        )
        secret = client.secrets.set(
            name="OPENAI_API_KEY",
            value="sk-abc123",
            type="api_key",
            scope="user",
            expose_as_env="OPENAI_API_KEY",
        )
        assert route.called
        body = json.loads(route.calls.last.request.content)
        assert body["name"] == "OPENAI_API_KEY"
        assert body["value"] == "sk-abc123"
        assert body["type"] == "api_key"
        assert body["scope"] == "user"
        assert body["expose_as_env"] == "OPENAI_API_KEY"
        assert secret["id"] == "sec_abc"

    def test_list_passes_scope_as_query(self, mock_api, client):
        route = mock_api.get("/egress/secrets", params={"scope": "user"}).respond(
            200, json={"data": [SECRET_JSON]}
        )
        result = client.secrets.list(scope="user")
        assert route.called
        assert len(result) == 1
        assert result[0]["id"] == "sec_abc"

    def test_get_calls_secret_id_path(self, mock_api, client):
        mock_api.get("/egress/secrets/sec_abc").respond(200, json={"data": SECRET_JSON})
        out = client.secrets.get("sec_abc")
        assert out["id"] == "sec_abc"

    def test_rotate_sends_patch(self, mock_api, client):
        route = mock_api.patch("/egress/secrets/sec_abc").respond(
            200, json={"data": SECRET_JSON}
        )
        client.secrets.rotate("sec_abc", "sk-new", expires_at="2027-01-01T00:00:00Z")
        body = json.loads(route.calls.last.request.content)
        assert body["value"] == "sk-new"
        assert body["expires_at"] == "2027-01-01T00:00:00Z"

    def test_delete_calls_delete(self, mock_api, client):
        route = mock_api.delete("/egress/secrets/sec_abc").respond(204)
        client.secrets.delete("sec_abc")
        assert route.called

    def test_connect_returns_oauth_flow(self, mock_api, client):
        route = mock_api.post("/egress/oauth/start").respond(
            200,
            json={
                "data": {
                    "authorize_url": "https://github.com/login/oauth/authorize?state=xyz",
                    "state": "xyz",
                }
            },
        )
        flow = client.secrets.connect("github", expose_as_env="GITHUB_TOKEN")
        assert route.called
        body = json.loads(route.calls.last.request.content)
        assert body["provider"] == "github"
        assert body["expose_as_env"] == "GITHUB_TOKEN"
        assert isinstance(flow, OauthFlow)
        assert flow.authorize_url.startswith("https://github.com/login/oauth/authorize")
        assert flow.state == "xyz"

    def test_oauth_wait_for_completion_polls_status(self, mock_api, client):
        mock_api.post("/egress/oauth/start").respond(
            200,
            json={
                "data": {
                    "authorize_url": "https://example.com/oauth?state=xyz",
                    "state": "xyz",
                }
            },
        )
        flow = client.secrets.connect("github")
        mock_api.get("/egress/oauth/status", params={"state": "xyz"}).respond(
            200,
            json={
                "data": {
                    "status": "completed",
                    "secret_id": "sec_new",
                    "state": "xyz",
                }
            },
        )
        result = flow.wait_for_completion(timeout=2.0, poll_interval=0.01)
        assert result["status"] == "completed"
        assert result["secret_id"] == "sec_new"

    def test_create_binding(self, mock_api, client):
        route = mock_api.post("/egress/bindings").respond(
            201, json={"data": {"id": "bnd_1"}}
        )
        client.secrets.create_binding(
            secret_id="sec_abc",
            resource_id="sbx_abc123",
            resource_type="sandbox",
            expose_as_env="OPENAI_API_KEY",
        )
        body = json.loads(route.calls.last.request.content)
        assert body["secret_id"] == "sec_abc"
        assert body["resource_id"] == "sbx_abc123"
        assert body["resource_type"] == "sandbox"
        assert body["expose_as_env"] == "OPENAI_API_KEY"


# ─── client.network ──────────────────────────────────────────────────────────


class TestEgressNetwork:
    def test_allow_posts_to_allowlist(self, mock_api, client):
        route = mock_api.post("/egress/allowlist").respond(
            201, json={"data": {"id": "rul_1", "host": "api.openai.com"}}
        )
        client.network.allow(
            "api.openai.com", methods=["GET", "POST"], path_glob="/v1/*"
        )
        body = json.loads(route.calls.last.request.content)
        assert body["host"] == "api.openai.com"
        assert body["effect"] == "allow"
        assert body["methods"] == ["GET", "POST"]
        assert body["path_glob"] == "/v1/*"

    def test_deny_posts_with_deny_effect(self, mock_api, client):
        route = mock_api.post("/egress/allowlist").respond(
            201, json={"data": {"id": "rul_2"}}
        )
        client.network.deny("169.254.169.254")
        body = json.loads(route.calls.last.request.content)
        assert body["host"] == "169.254.169.254"
        assert body["effect"] == "deny"

    def test_lockdown_patches_policy(self, mock_api, client):
        route = mock_api.patch("/egress/policies").respond(200, json={"data": {}})
        client.network.lockdown()
        body = json.loads(route.calls.last.request.content)
        assert body["mode"] == "enforce"

    def test_observe_patches_audit_only(self, mock_api, client):
        route = mock_api.patch("/egress/policies").respond(200, json={"data": {}})
        client.network.observe()
        body = json.loads(route.calls.last.request.content)
        assert body["mode"] == "audit_only"

    def test_suggestions_passes_resource_id(self, mock_api, client):
        route = mock_api.get(
            "/egress/audit/suggestions",
            params={"resource_id": "sbx_abc123", "since": "7d"},
        ).respond(200, json={"data": [{"host": "api.openai.com"}]})
        out = client.network.suggestions(resource_id="sbx_abc123")
        assert route.called
        assert len(out) == 1

    def test_policies_returns_list(self, mock_api, client):
        mock_api.get("/egress/policies").respond(
            200, json={"data": [{"id": "pol_1"}, {"id": "pol_2"}]}
        )
        out = client.network.policies()
        assert len(out) == 2


# ─── client.audit ────────────────────────────────────────────────────────────


class TestEgressAudit:
    def test_list_returns_events(self, mock_api, client):
        mock_api.get("/egress/audit").respond(
            200,
            json={
                "data": [
                    {"id": "evt_1", "host": "api.openai.com"},
                    {"id": "evt_2", "host": "github.com"},
                ]
            },
        )
        out = client.audit.list()
        assert len(out) == 2
        assert out[0]["id"] == "evt_1"

    def test_list_passes_filters(self, mock_api, client):
        route = mock_api.get(
            "/egress/audit",
            params={"resource_id": "sbx_abc123", "host": "api.openai.com"},
        ).respond(200, json={"data": []})
        client.audit.list(resource_id="sbx_abc123", host="api.openai.com")
        assert route.called

    def test_get_returns_single_event(self, mock_api, client):
        mock_api.get("/egress/audit/evt_1").respond(
            200, json={"data": {"id": "evt_1", "host": "api.openai.com"}}
        )
        out = client.audit.get("evt_1")
        assert out["id"] == "evt_1"


# ─── sandbox.secrets / sandbox.network / sandbox.audit ───────────────────────


class TestSandboxScopedEgress:
    def test_sandbox_secrets_set_injects_resource_id(self, mock_api, client):
        sbx = _get_sandbox(mock_api, client)
        route = mock_api.post("/egress/secrets").respond(
            201, json={"data": SECRET_JSON}
        )
        sbx.secrets.set(name="OPENAI_API_KEY", value="sk-abc")
        body = json.loads(route.calls.last.request.content)
        assert body["resource_id"] == "sbx_abc123"
        assert body["resource_type"] == "sandbox"

    def test_sandbox_audit_list_passes_resource_id(self, mock_api, client):
        sbx = _get_sandbox(mock_api, client)
        route = mock_api.get(
            "/egress/audit",
            params={"resource_id": "sbx_abc123", "resource_type": "sandbox"},
        ).respond(200, json={"data": []})
        sbx.audit.list()
        assert route.called

    def test_sandbox_network_allow_scopes_to_sandbox(self, mock_api, client):
        sbx = _get_sandbox(mock_api, client)
        route = mock_api.post("/egress/allowlist").respond(
            201, json={"data": {"id": "rul_1"}}
        )
        sbx.network.allow("api.openai.com")
        body = json.loads(route.calls.last.request.content)
        assert body["resource_id"] == "sbx_abc123"
        assert body["resource_type"] == "sandbox"
        assert body["host"] == "api.openai.com"
        assert body["effect"] == "allow"

    def test_sandbox_network_lockdown_scopes_to_sandbox(self, mock_api, client):
        sbx = _get_sandbox(mock_api, client)
        route = mock_api.patch("/egress/policies").respond(200, json={"data": {}})
        sbx.network.lockdown()
        body = json.loads(route.calls.last.request.content)
        assert body["mode"] == "enforce"
        assert body["resource_id"] == "sbx_abc123"
        assert body["resource_type"] == "sandbox"
