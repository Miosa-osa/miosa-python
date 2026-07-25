"""Tests for sandbox.update()."""

from __future__ import annotations

import json

import httpx

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


class TestSandboxAgentWorkspace:
    def test_get_or_create_resumes_paused_named_sandbox(self, mock_api, client):
        mock_api.get("/sandboxes/by-name/customer%20builder").respond(
            200, json={"data": {**SANDBOX_JSON, "name": "customer builder", "state": "paused"}}
        )
        resume = mock_api.post("/sandboxes/sbx_abc123/resume").respond(
            200, json={"data": {**SANDBOX_JSON, "name": "customer builder", "state": "running"}}
        )

        sb = client.sandboxes.get_or_create("customer builder")

        assert sb.state == "running"
        assert resume.calls.call_count == 1

    def test_create_agent_workspace_creates_missing_named_sandbox(self, mock_api, client):
        captured: dict = {}

        mock_api.get("/sandboxes/by-name/new-builder").respond(404, json={"message": "missing"})

        def capture_create(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"data": {**SANDBOX_JSON, "name": "new-builder"}})

        mock_api.post("/sandboxes").mock(side_effect=capture_create)
        mock_api.get("/sandboxes/sbx_abc123/readiness/stream").respond(
            200,
            content=b"event: ready\ndata: {}\n\n",
            headers={"content-type": "text/event-stream"},
        )

        sb = client.sandboxes.create_agent_workspace(
            "new-builder",
            external_workspace_id="clinic-123",
            external_user_id="dr-smith",
        )

        assert sb.id == SANDBOX_JSON["id"]
        body = captured["body"]
        assert body["name"] == "new-builder"
        assert body["timeout_sec"] == 86_400
        assert body["idle_timeout_sec"] == 1800
        assert body["metadata"]["miosa_workspace_kind"] == "agent_workspace"
        assert body["metadata"]["miosa_persistent"] is True
        assert body["metadata"]["snapshot_expiration_sec"] == 2_592_000
        assert body["metadata"]["keep_last_snapshots"] == 1
        assert body["external_workspace_id"] == "clinic-123"
        assert body["external_user_id"] == "dr-smith"

    def test_create_persistent_policy_sets_defaults_and_metadata(self, mock_api, client):
        captured: dict = {}

        def capture_create(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"data": {**SANDBOX_JSON, "name": "builder"}})

        mock_api.post("/sandboxes").mock(side_effect=capture_create)

        client.sandboxes.create(
            name="builder",
            persistent=True,
            snapshot_expiration_days=14,
            keep_last_snapshots={"count": 2, "expiration_sec": 2_592_000},
        )

        body = captured["body"]
        assert body["timeout_sec"] == 86_400
        assert body["idle_timeout_sec"] == 1_800
        assert body["metadata"]["miosa_persistent"] is True
        assert body["metadata"]["snapshot_expiration_sec"] == 1_209_600
        assert body["metadata"]["keep_last_snapshots"] == {
            "count": 2,
            "expiration_sec": 2_592_000,
        }

    def test_extend_calls_timeout_endpoint(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json={"data": SANDBOX_JSON})
        route = mock_api.post("/sandboxes/sbx_abc123/extend").respond(
            200, json={"data": {**SANDBOX_JSON, "timeout_sec": 86_400}}
        )

        sb = client.sandboxes.get("sbx_abc123")
        sb.extend(86_400)

        body = json.loads(route.calls.last.request.content)
        assert body["timeout_sec"] == 86_400
        assert sb.timeout_sec == 86_400
