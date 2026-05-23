"""Tests for the Workspaces resource."""

from __future__ import annotations

import pytest

from miosa.types import WorkspaceData

from .conftest import COMPUTER_JSON

WORKSPACE_JSON = {
    "id": "ws_abc",
    "name": "prod",
    "slug": "prod",
    "tenant_id": "tnt_1",
    "description": "prod team",
    "metadata": {"env": "prod"},
    "created_at": "2026-04-01T00:00:00Z",
    "updated_at": "2026-04-01T00:00:00Z",
}


class TestWorkspaces:
    def test_create_sends_name_and_parses_response(self, mock_api, client):
        route = mock_api.post("/workspaces").respond(200, json={"data": WORKSPACE_JSON})
        ws = client.workspaces.create(name="prod", description="prod team")
        assert isinstance(ws, WorkspaceData)
        assert ws.id == "ws_abc"
        assert ws.name == "prod"
        assert route.called
        # Verify request body shape
        sent = route.calls.last.request.content
        assert b'"name":"prod"' in sent
        assert b'"description":"prod team"' in sent

    def test_list_returns_typed_models(self, mock_api, client):
        mock_api.get("/workspaces").respond(
            200, json={"data": [WORKSPACE_JSON, WORKSPACE_JSON]}
        )
        items = client.workspaces.list()
        assert len(items) == 2
        assert all(isinstance(w, WorkspaceData) for w in items)

    def test_get_by_id(self, mock_api, client):
        mock_api.get("/workspaces/ws_abc").respond(
            200, json={"data": WORKSPACE_JSON}
        )
        ws = client.workspaces.get("ws_abc")
        assert ws.id == "ws_abc"

    def test_update_sends_patch(self, mock_api, client):
        updated = {**WORKSPACE_JSON, "name": "staging"}
        route = mock_api.patch("/workspaces/ws_abc").respond(
            200, json={"data": updated}
        )
        ws = client.workspaces.update("ws_abc", name="staging")
        assert ws.name == "staging"
        assert route.called

    def test_delete_sends_delete(self, mock_api, client):
        route = mock_api.delete("/workspaces/ws_abc").respond(200, json={})
        client.workspaces.delete("ws_abc")
        assert route.called

    def test_list_computers_returns_bound_computers(self, mock_api, client):
        mock_api.get("/workspaces/ws_abc/computers").respond(
            200, json={"computers": [COMPUTER_JSON]}
        )
        computers = client.workspaces.list_computers("ws_abc")
        assert len(computers) == 1
        assert computers[0].id == "comp_abc123"
        assert computers[0].name == "test-agent"


@pytest.mark.asyncio
class TestAsyncWorkspaces:
    async def test_async_create(self, mock_api, async_client):
        mock_api.post("/workspaces").respond(200, json={"data": WORKSPACE_JSON})
        ws = await async_client.workspaces.create(name="prod")
        assert ws.id == "ws_abc"
        await async_client.close()
