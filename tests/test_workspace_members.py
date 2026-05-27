"""Tests for WorkspaceMembers resource."""

from __future__ import annotations

import pytest

from .conftest import API_KEY, BASE_URL

MEMBER_JSON = {
    "user_id": "usr_abc",
    "email": "alice@example.com",
    "name": "Alice",
    "avatar_url": None,
    "role": "member",
    "joined_at": "2026-05-01T10:00:00Z",
    "added_by": None,
}

MEMBER_RECORD_JSON = {
    "user_id": "usr_def",
    "workspace_id": "ws-uuid",
    "role": "member",
    "joined_at": "2026-05-22T09:00:00Z",
    "added_by": "usr_abc",
}


class TestWorkspaceMembers:
    def test_list_calls_correct_path_and_returns_list(self, mock_api, client):
        mock_api.get("/workspaces/ws-uuid/members").respond(
            200, json={"data": [MEMBER_JSON, MEMBER_JSON]}
        )
        members = client.workspace_members.list("ws-uuid")
        assert len(members) == 2
        assert members[0]["user_id"] == "usr_abc"
        assert members[0]["email"] == "alice@example.com"

    def test_list_returns_empty_list_when_no_members(self, mock_api, client):
        mock_api.get("/workspaces/ws-uuid/members").respond(
            200, json={"data": []}
        )
        members = client.workspace_members.list("ws-uuid")
        assert members == []

    def test_add_posts_user_id_and_role(self, mock_api, client):
        route = mock_api.post("/workspaces/ws-uuid/members").respond(
            201, json={"data": MEMBER_RECORD_JSON}
        )
        record = client.workspace_members.add("ws-uuid", user_id="usr_def", role="member")
        assert record["user_id"] == "usr_def"
        assert record["role"] == "member"
        assert route.called
        body = route.calls.last.request.content
        assert b"usr_def" in body
        assert b"member" in body

    def test_update_role_patches_correct_path(self, mock_api, client):
        updated = {**MEMBER_RECORD_JSON, "role": "admin"}
        route = mock_api.patch("/workspaces/ws-uuid/members/usr_def").respond(
            200, json={"data": updated}
        )
        record = client.workspace_members.update_role("ws-uuid", "usr_def", role="admin")
        assert record["role"] == "admin"
        assert route.called
        body = route.calls.last.request.content
        assert b"admin" in body

    def test_remove_sends_delete(self, mock_api, client):
        route = mock_api.delete("/workspaces/ws-uuid/members/usr_def").respond(
            200, json={"deleted": True}
        )
        result = client.workspace_members.remove("ws-uuid", "usr_def")
        assert result.get("deleted") is True
        assert route.called
