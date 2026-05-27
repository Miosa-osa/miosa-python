"""Phase 6 governance resource tests."""

from __future__ import annotations

import pytest
import respx
import httpx

from miosa import Miosa
from miosa.resources.governance import EffectivePolicy

API_KEY = "msk_u_test_key_12345"
BASE_URL = "https://api.miosa.ai/api/v1"


@pytest.fixture()
def mock_api():
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as rx:
        yield rx


@pytest.fixture()
def client():
    return Miosa(api_key=API_KEY, base_url=BASE_URL)


# ── tenant.policy ─────────────────────────────────────────────────────────────

class TestTenantPolicy:
    def test_get_returns_policy(self, mock_api, client):
        mock_api.get("/tenant/policy").respond(200, json={"data": {"quotas": {"max_sandboxes": 10}}})
        result = client.tenant.policy.get()
        assert result["quotas"]["max_sandboxes"] == 10

    def test_set_sends_body(self, mock_api, client):
        route = mock_api.put("/tenant/policy").respond(200, json={"data": {"quotas": {"max_sandboxes": 5}}})
        result = client.tenant.policy.set({"quotas": {"max_sandboxes": 5}})
        assert route.called
        assert result["quotas"]["max_sandboxes"] == 5

    def test_delete_sends_delete(self, mock_api, client):
        route = mock_api.delete("/tenant/policy").respond(204)
        client.tenant.policy.delete()
        assert route.called


# ── tenant.members ────────────────────────────────────────────────────────────

class TestTenantMembers:
    def test_list_returns_members(self, mock_api, client):
        mock_api.get("/tenant/members").respond(200, json={"data": [{"id": "m1", "email": "a@b.com", "role": "admin"}]})
        members = client.tenant.members.list()
        assert len(members) == 1
        assert members[0]["role"] == "admin"

    def test_invite_posts_email_and_role(self, mock_api, client):
        route = mock_api.post("/tenant/members").respond(200, json={"data": {"id": "m2", "email": "x@y.com", "role": "developer"}})
        result = client.tenant.members.invite("x@y.com", "developer")
        assert route.called
        assert result["role"] == "developer"

    def test_update_role(self, mock_api, client):
        route = mock_api.patch("/tenant/members/m1/role").respond(200, json={"data": {"id": "m1", "role": "admin"}})
        result = client.tenant.members.update_role("m1", "admin")
        assert route.called

    def test_remove(self, mock_api, client):
        route = mock_api.delete("/tenant/members/m1").respond(204)
        client.tenant.members.remove("m1")
        assert route.called

    def test_transfer_ownership(self, mock_api, client):
        route = mock_api.post("/tenant/transfer-ownership").respond(200, json={"data": {"transferred": True}})
        result = client.tenant.members.transfer_ownership("user_new_owner")
        assert route.called


# ── workspaces (governance) ───────────────────────────────────────────────────

class TestGovernanceWorkspaces:
    def test_list_workspaces(self, mock_api, client):
        mock_api.get("/workspaces").respond(200, json={"data": [{"id": "ws_1", "name": "alpha"}]})
        items = client.workspaces.list()
        assert len(items) == 1
        assert items[0]["id"] == "ws_1"

    def test_create_workspace(self, mock_api, client):
        route = mock_api.post("/workspaces").respond(200, json={"data": {"id": "ws_2", "name": "beta"}})
        result = client.workspaces.create("beta")
        assert route.called
        assert result["id"] == "ws_2"

    def test_workspace_policy_get(self, mock_api, client):
        mock_api.get("/workspaces/ws_1/policy").respond(200, json={"data": {"quotas": {"max_sandboxes": 3}}})
        result = client.workspaces("ws_1").policy.get()
        assert result["quotas"]["max_sandboxes"] == 3

    def test_workspace_policy_set(self, mock_api, client):
        route = mock_api.put("/workspaces/ws_1/policy").respond(200, json={"data": {"quotas": {}}})
        client.workspaces("ws_1").policy.set({"quotas": {"max_sandboxes": 3}})
        assert route.called

    def test_workspace_members_list(self, mock_api, client):
        mock_api.get("/workspaces/ws_1/members").respond(200, json={"data": [{"id": "m1", "role": "developer"}]})
        members = client.workspaces("ws_1").members.list()
        assert members[0]["role"] == "developer"

    def test_workspace_members_invite(self, mock_api, client):
        route = mock_api.post("/workspaces/ws_1/members").respond(200, json={"data": {"id": "m2"}})
        client.workspaces("ws_1").members.invite("bob@acme.com", "viewer")
        assert route.called

    def test_workspace_transfer(self, mock_api, client):
        route = mock_api.post("/workspaces/ws_1/transfer").respond(200, json={"data": {"transferred": 2}})
        result = client.workspaces("ws_1").transfer(["sbx_1", "sbx_2"], "ws_2")
        assert route.called


# ── external_users policy ─────────────────────────────────────────────────────

class TestExternalUserPolicy:
    def test_get_policy(self, mock_api, client):
        mock_api.get("/external-users/alice/policy").respond(200, json={"data": {"lifecycle": {}}})
        result = client.external_users("alice").policy.get()
        assert "lifecycle" in result

    def test_set_policy(self, mock_api, client):
        route = mock_api.put("/external-users/alice/policy").respond(200, json={"data": {}})
        client.external_users("alice").policy.set({"lifecycle": {"default_idle_timeout_sec": 300}})
        assert route.called

    def test_effective_policy_typed(self, mock_api, client):
        mock_api.get("/external-users/alice/effective-policy").respond(200, json={
            "lifecycle": {
                "default_idle_timeout_sec": {"value": 600, "source": "user"},
                "default_timeout_sec": {"value": 86400, "source": "tenant"},
            },
            "quotas": {
                "max_sandboxes": {"value": 5, "source": "workspace"},
            }
        })
        eff = client.external_users("alice").policy.effective()
        assert isinstance(eff, EffectivePolicy)
        assert eff.lifecycle.default_idle_timeout_sec.value == 600
        assert eff.lifecycle.default_idle_timeout_sec.source == "user"
        assert eff.lifecycle.default_timeout_sec.source == "tenant"
        assert eff.quotas.max_sandboxes.value == 5
        assert eff.quotas.max_sandboxes.source == "workspace"


# ── bulk ops ──────────────────────────────────────────────────────────────────

class TestBulkOps:
    def test_bulk_sandboxes_pause(self, mock_api, client):
        route = mock_api.post("/bulk/sandboxes/pause").respond(200, json={"queued": 3, "job_id": "job_1"})
        result = client.bulk.sandboxes.pause(ids=["sbx_1", "sbx_2", "sbx_3"])
        assert route.called
        assert result["job_id"] == "job_1"

    def test_bulk_sandboxes_destroy_with_filter(self, mock_api, client):
        route = mock_api.post("/bulk/sandboxes/destroy").respond(200, json={"queued": 5, "job_id": "job_2"})
        result = client.bulk.sandboxes.destroy(filter={"state": "idle"})
        assert route.called
        assert result["queued"] == 5

    def test_bulk_policy_apply(self, mock_api, client):
        route = mock_api.post("/bulk/policy/apply").respond(200, json={"queued": 10, "job_id": "job_3"})
        result = client.bulk.policy.apply(
            tier="external_user",
            ids_or_filter=["u1", "u2"],
            policy={"quotas": {"max_sandboxes": 3}},
        )
        assert route.called
        assert result["job_id"] == "job_3"

    def test_bulk_jobs_get(self, mock_api, client):
        mock_api.get("/bulk/jobs/job_1").respond(200, json={"data": {"id": "job_1", "status": "completed", "processed": 3}})
        job = client.bulk.jobs.get("job_1")
        assert job["status"] == "completed"
        assert job["processed"] == 3


# ── api_keys.create_scoped ────────────────────────────────────────────────────

class TestApiKeysScoped:
    def test_create_scoped_posts_correctly(self, mock_api, client):
        route = mock_api.post("/api-keys/scoped").respond(200, json={"data": {"id": "key_1", "token": "msk_l2_abc"}})
        result = client.api_keys.create_scoped(
            external_user_id="alice-42",
            scopes=["sandboxes:read", "sandboxes:exec"],
            expires_at="2026-12-31T00:00:00Z",
        )
        assert route.called
        assert result["token"] == "msk_l2_abc"

    def test_create_scoped_without_expires(self, mock_api, client):
        route = mock_api.post("/api-keys/scoped").respond(200, json={"data": {"id": "key_2"}})
        client.api_keys.create_scoped(external_user_id="bob", scopes=["sandboxes:read"])
        assert route.called


# ── admin.impersonate ─────────────────────────────────────────────────────────

class TestAdminImpersonate:
    def test_impersonate_posts_correctly(self, mock_api, client):
        route = mock_api.post("/admin/impersonate").respond(200, json={"token": "msi_abc", "expires_at": "2026-06-01T00:00:00Z"})
        result = client.admin.impersonate("alice-42", ttl_sec=1800)
        assert route.called
        assert result["token"] == "msi_abc"

    def test_impersonate_default_ttl(self, mock_api, client):
        route = mock_api.post("/admin/impersonate").respond(200, json={"token": "msi_xyz"})
        client.admin.impersonate("bob")
        assert route.called
        body = route.calls.last.request.content
        assert b'"ttl_sec": 3600' in body or b'"ttl_sec":3600' in body


# ── billing ───────────────────────────────────────────────────────────────────

class TestBilling:
    def test_invoices_list(self, mock_api, client):
        mock_api.get("/billing/invoices").respond(200, json={"data": [{"id": "inv_1", "amount": 5000}]})
        invoices = client.billing.invoices.list()
        assert invoices[0]["id"] == "inv_1"

    def test_invoices_get(self, mock_api, client):
        mock_api.get("/billing/invoices/inv_1").respond(200, json={"data": {"id": "inv_1", "amount": 5000, "line_items": []}})
        inv = client.billing.invoices.get("inv_1")
        assert inv["id"] == "inv_1"

    def test_payment_methods(self, mock_api, client):
        mock_api.get("/billing/payment-methods").respond(200, json={"data": [{"id": "pm_1", "brand": "visa", "last4": "4242"}]})
        methods = client.billing.payment_methods()
        assert methods[0]["brand"] == "visa"

    def test_upcoming(self, mock_api, client):
        mock_api.get("/billing/upcoming").respond(200, json={"data": {"amount": 1200, "period_end": "2026-06-01"}})
        upcoming = client.billing.upcoming()
        assert upcoming["amount"] == 1200
