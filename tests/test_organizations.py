from __future__ import annotations

import pytest

from miosa import AsyncMiosa, Miosa
from miosa.errors import ValidationError

from .conftest import BASE_URL


def test_organization_contract_and_members(mock_api):
    mock_api.get("/platform/tenants").respond(
        200, json={"data": [{"id": "ten_1", "slug": "panther", "role": "admin"}]}
    )
    mock_api.get("/platform/tenants/current").respond(
        200, json={"id": "ten_1", "slug": "panther", "branding": {}}
    )
    switch = mock_api.post("/platform/tenants/panther/switch").respond(
        200, json={"tenant": {"id": "ten_1"}, "token": "jwt", "refresh_token": "refresh"}
    )
    members = mock_api.get("/tenants/ten_1/members").respond(
        200, json={"members": [{"user_id": "usr_1"}], "total": 1}
    )
    add = mock_api.post("/tenants/ten_1/members").respond(
        201, json={"id": "mem_2", "user_id": "usr_2", "role": "admin"}
    )
    remove = mock_api.delete("/tenants/ten_1/members/usr_2").respond(200, json={"removed": True})
    client = Miosa(access_token="jwt", tenant="panther", base_url=BASE_URL, max_retries=0)

    assert client.organizations.list()[0]["role"] == "admin"
    assert client.organizations.current()["branding"] == {}
    assert client.organizations.switch("panther")["token"] == "jwt"
    assert client.organizations.members.list("ten_1")["total"] == 1
    assert client.organizations.members.add("ten_1", "usr_2", "admin")["role"] == "admin"
    assert client.organizations.members.remove("ten_1", "usr_2")["removed"] is True
    assert switch.calls.last.request.headers["x-miosa-tenant"] == "panther"
    assert members.called and add.called and remove.called
    client.close()


def test_organization_invite_lifecycle(mock_api, client):
    create = mock_api.post("/tenants/ten_1/invites").respond(
        201,
        json={
            "data": {
                "invite_id": "inv_1",
                "email": "partner@example.com",
                "role": "member",
                "expires_at": "2026-07-21T00:00:00Z",
                "invite_url": "https://miosa.ai/invites/token",
            }
        },
    )
    mock_api.get("/tenants/ten_1/invites").respond(
        200,
        json={"data": [{"id": "inv_1", "email": "partner@example.com"}], "total": 1},
    )
    mock_api.delete("/tenants/ten_1/invites/inv_1").respond(
        200, json={"invite_id": "inv_1", "revoked": True}
    )

    invite = client.organizations.invites.create("ten_1", email="partner@example.com")
    assert invite["invite_url"] == "https://miosa.ai/invites/token"
    assert client.organizations.invites.list("ten_1")[0]["id"] == "inv_1"
    assert client.organizations.invites.revoke("ten_1", "inv_1")["revoked"] is True
    assert create.calls.last.request.content == b'{"email":"partner@example.com","role":"member"}'


def test_rejects_ambiguous_credentials():
    with pytest.raises(ValueError, match="either api_key or access_token"):
        Miosa(api_key="msk_test", access_token="jwt")


async def test_async_organization_context_header(mock_api):
    route = mock_api.get("/platform/tenants").respond(
        200, json={"data": [{"id": "ten_1", "slug": "panther"}]}
    )
    client = AsyncMiosa(
        access_token="user.jwt",
        tenant="panther-defense",
        base_url=BASE_URL,
        max_retries=0,
    )

    assert (await client.organizations.list())[0]["slug"] == "panther"
    assert route.calls.last.request.headers["x-miosa-tenant"] == "panther-defense"
    await client.close()


def test_flat_structured_error_is_preserved(mock_api, client):
    mock_api.get("/platform/tenants/current").respond(
        422,
        json={
            "error": "EMAIL_MISMATCH",
            "detail": "Invite email does not match",
            "details": {"expected": "a@example.com"},
            "request_id": "req_body",
        },
    )
    with pytest.raises(ValidationError) as caught:
        client.organizations.current()
    assert caught.value.code == "EMAIL_MISMATCH"
    assert caught.value.message == "Invite email does not match"
    assert caught.value.details == {"expected": "a@example.com"}
    assert caught.value.status_code == 422
    assert caught.value.request_id == "req_body"
