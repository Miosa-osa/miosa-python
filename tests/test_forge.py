"""Contract tests for the verified Forge repository namespace."""

from __future__ import annotations

from typing import Any

import pytest

from miosa import AsyncMiosa, ForgeContractError, ForgeUnavailableError, Miosa
from miosa.errors import NotFoundError
from miosa.resources.forge import (
    AsyncForge,
    AsyncForgeRepositories,
    Forge,
    ForgeRepositories,
)

REPOSITORY = {
    "id": "96a47492-d5e1-4e50-bef2-2f9d1136a326",
    "name": "Platform",
    "slug": "platform",
    "default_branch": "main",
    "visibility": "private",
    "state": "active",
    "clone_ready": True,
    "clone_url": "https://forge.miosa.ai/acme/platform.git",
    "project_ids": [],
    "created_at": "2026-08-14T12:00:00Z",
    "updated_at": "2026-08-14T12:00:00Z",
}

REFS = {
    "default_branch": "main",
    "head_oid": "a" * 40,
    "branches": [{"name": "main", "oid": "a" * 40, "is_default": True}],
    "tags": [],
}
TREE = {
    "ref": "main",
    "commit_oid": "a" * 40,
    "path": "",
    "entries": [
        {"name": "README.md", "path": "README.md", "type": "blob", "oid": "b" * 40, "size": 5}
    ],
    "truncated": False,
}
BLOB = {
    "ref": "main",
    "commit_oid": "a" * 40,
    "path": "README.md",
    "oid": "b" * 40,
    "size": 5,
    "encoding": "utf-8",
    "content": "hello",
}
HISTORY = {
    "ref": "main",
    "path": "",
    "commits": [
        {
            "oid": "a" * 40,
            "short_oid": "aaaaaaa",
            "subject": "initial",
            "author_name": "Ada",
            "author_email": "ada@example.test",
            "authored_at": "2026-08-14T12:00:00Z",
            "committer_name": "Ada",
            "committed_at": "2026-08-14T12:00:00Z",
            "parents": [],
        }
    ],
    "page": {"has_more": False, "next_cursor": None},
}


class SyncTransport:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        self.calls.append((method, path, kwargs))
        return self.response


class AsyncTransport:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        self.calls.append((method, path, kwargs))
        return self.response


def test_clients_expose_only_verified_forge_namespace() -> None:
    client = Miosa(api_key="msk_test")
    async_client = AsyncMiosa(api_key="msk_test")
    try:
        assert isinstance(client.forge, Forge)
        assert isinstance(client.forge.repositories, ForgeRepositories)
        assert isinstance(async_client.forge, AsyncForge)
        assert isinstance(async_client.forge.repositories, AsyncForgeRepositories)
        assert not hasattr(client.forge, "pull_requests")
        assert not hasattr(client.forge, "change_requests")
        assert not hasattr(client.forge, "checks")
        assert not hasattr(client.forge, "releases")
    finally:
        client.close()


def test_sync_repository_contract_and_idempotency() -> None:
    transport = SyncTransport({"data": REPOSITORY})
    repositories = ForgeRepositories(transport)  # type: ignore[arg-type]

    created = repositories.create(
        "Platform",
        slug="platform",
        default_branch="main",
        visibility="private",
        project_ids=["project-1"],
        idempotency_key="forge-create-1",
    )
    transport.response = {"data": [REPOSITORY]}
    listed = repositories.list()
    transport.response = {"data": REPOSITORY}
    shown = repositories.get(REPOSITORY["id"])

    class DeleteResponse:
        headers = {"x-forge-operation-id": REPOSITORY["id"], "idempotency-replayed": "false"}

    transport.response = DeleteResponse()
    repositories.delete(REPOSITORY["id"])

    assert created["id"] == REPOSITORY["id"]
    assert listed == [REPOSITORY]
    assert shown == REPOSITORY
    assert transport.calls == [
        (
            "POST",
            "/forge/repositories",
            {
                "json_body": {
                    "name": "Platform",
                    "slug": "platform",
                    "default_branch": "main",
                    "visibility": "private",
                    "project_ids": ["project-1"],
                },
                "headers": {"Idempotency-Key": "forge-create-1"},
            },
        ),
        ("GET", "/forge/repositories", {"params": None}),
        ("GET", f"/forge/repositories/{REPOSITORY['id']}", {}),
        (
            "DELETE",
            f"/forge/repositories/{REPOSITORY['id']}",
            {"raw_response": True},
        ),
    ]


def test_public_repository_matches_canonical_contract() -> None:
    public_repository = {**REPOSITORY, "visibility": "public"}
    transport = SyncTransport({"data": [public_repository]})

    assert ForgeRepositories(transport).list()[0]["visibility"] == "public"  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_async_repository_contract() -> None:
    transport = AsyncTransport({"data": REPOSITORY})
    repositories = AsyncForgeRepositories(transport)  # type: ignore[arg-type]

    created = await repositories.create("Platform")
    transport.response = {"data": [REPOSITORY]}
    listed = await repositories.list()
    transport.response = {"data": REPOSITORY}
    shown = await repositories.get(REPOSITORY["id"])

    class DeleteResponse:
        headers = {"x-forge-operation-id": REPOSITORY["id"], "idempotency-replayed": "false"}

    transport.response = DeleteResponse()
    await repositories.delete(REPOSITORY["id"])

    assert created["slug"] == "platform"
    assert listed == [REPOSITORY]
    assert shown == REPOSITORY
    assert transport.calls[1] == (
        "GET",
        "/forge/repositories",
        {"params": None},
    )


def test_repository_response_drift_fails_closed() -> None:
    transport = SyncTransport({"data": [{"id": "only-an-id"}]})
    with pytest.raises(ForgeContractError, match="missing name"):
        ForgeRepositories(transport).list()  # type: ignore[arg-type]


def test_sync_repository_content_contract_and_pagination() -> None:
    transport = SyncTransport({"data": REFS})
    repositories = ForgeRepositories(transport)  # type: ignore[arg-type]
    assert repositories.refs("repo-1") == REFS
    transport.response = {"data": TREE}
    assert repositories.tree("repo-1", ref="main", path="src") == TREE
    transport.response = {"data": BLOB}
    assert repositories.blob("repo-1", "README.md", ref="main") == BLOB
    assert repositories.readme("repo-1") == BLOB
    transport.response = {"data": HISTORY}
    assert repositories.commits("repo-1", limit=25, cursor="cursor-1") == HISTORY
    assert transport.calls[-1] == (
        "GET",
        "/forge/repositories/repo-1/commits",
        {"params": {"limit": 25, "cursor": "cursor-1"}},
    )


@pytest.mark.asyncio
async def test_async_repository_content_contract() -> None:
    transport = AsyncTransport({"data": BLOB})
    repository = AsyncForgeRepositories(transport)  # type: ignore[arg-type]
    assert await repository.blob("repo-1", "README.md", ref="main") == BLOB
    assert transport.calls == [
        ("GET", "/forge/repositories/repo-1/blob", {"params": {"ref": "main", "path": "README.md"}})
    ]


def test_disabled_forge_raises_typed_error() -> None:
    class DisabledTransport(SyncTransport):
        def request(self, method: str, path: str, **kwargs: Any) -> Any:
            raise NotFoundError("not found", status_code=404, code="FORGE_DISABLED")

    with pytest.raises(ForgeUnavailableError):
        ForgeRepositories(DisabledTransport(None)).create("Platform")  # type: ignore[arg-type]
