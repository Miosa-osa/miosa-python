"""Verified MIOSA Forge repository API."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any, Literal, NoReturn, TypedDict, cast
from urllib.parse import quote
from uuid import uuid4

from ..errors import MiosaError

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport

ForgeRepositoryVisibility = Literal["public", "private", "internal"]
ForgeRepositoryState = Literal["provisioning", "active", "error", "deletion_pending", "deleted"]


class ForgeRepository(TypedDict):
    id: str
    name: str
    slug: str
    default_branch: str
    visibility: ForgeRepositoryVisibility
    state: ForgeRepositoryState
    clone_ready: bool
    clone_url: str | None
    project_ids: list[str]
    created_at: str
    updated_at: str


class ForgeNamedRef(TypedDict):
    name: str
    oid: str


class ForgeBranch(ForgeNamedRef):
    is_default: bool


class ForgeRepositoryRefs(TypedDict):
    default_branch: str
    head_oid: str | None
    branches: list[ForgeBranch]
    tags: list[ForgeNamedRef]


class ForgeTreeEntry(TypedDict):
    name: str
    path: str
    type: Literal["blob", "tree"]
    oid: str
    size: int | None


class ForgeRepositoryTree(TypedDict):
    ref: str
    commit_oid: str
    path: str
    entries: list[ForgeTreeEntry]
    truncated: bool


class ForgeRepositoryBlob(TypedDict):
    ref: str
    commit_oid: str
    path: str
    oid: str
    size: int
    encoding: Literal["utf-8", "base64"]
    content: str


class ForgeCommit(TypedDict):
    oid: str
    short_oid: str
    subject: str
    author_name: str
    author_email: str
    authored_at: str
    committer_name: str
    committed_at: str
    parents: list[str]


class ForgeCommitPage(TypedDict):
    has_more: bool
    next_cursor: str | None


class ForgeCommitHistory(TypedDict):
    ref: str
    path: str
    commits: list[ForgeCommit]
    page: ForgeCommitPage


class ForgeContractError(MiosaError):
    """Raised when a Forge response does not match the SDK contract."""


class ForgeUnavailableError(MiosaError):
    """Raised when Forge is not enabled for the organization."""


class ForgeStorageError(MiosaError):
    """Raised when Forge repository storage cannot complete an operation."""


class ForgePolicyViolationError(MiosaError):
    """Raised when organization policy rejects a Forge operation."""


_REPOSITORIES = "/forge/repositories"
_VISIBILITIES = {"public", "private", "internal"}
_STATES = {"provisioning", "active", "error", "deletion_pending", "deleted"}
_REQUIRED_STRING_FIELDS = (
    "id",
    "name",
    "slug",
    "default_branch",
    "visibility",
    "state",
    "created_at",
    "updated_at",
)


def _repository_path(repository_id: str) -> str:
    return f"{_REPOSITORIES}/{quote(repository_id, safe='')}"


def _repository(payload: Any) -> ForgeRepository:
    if not isinstance(payload, dict):
        raise ForgeContractError(
            "Forge returned an invalid repository",
            status_code=502,
            code="FORGE_CONTRACT_ERROR",
            body=payload,
        )
    for field in _REQUIRED_STRING_FIELDS:
        value = payload.get(field)
        if not isinstance(value, str) or not value:
            raise ForgeContractError(
                f"Forge repository is missing {field}",
                status_code=502,
                code="FORGE_CONTRACT_ERROR",
                body=payload,
            )
    if payload["visibility"] not in _VISIBILITIES:
        raise ForgeContractError(
            "Forge repository has an invalid visibility",
            status_code=502,
            code="FORGE_CONTRACT_ERROR",
            body=payload,
        )
    if payload["state"] not in _STATES:
        raise ForgeContractError(
            "Forge repository has an invalid state",
            status_code=502,
            code="FORGE_CONTRACT_ERROR",
            body=payload,
        )
    clone_url = payload.get("clone_url")
    clone_ready = payload.get("clone_ready")
    project_ids = payload.get("project_ids")
    if not isinstance(clone_ready, bool) or (
        clone_url is not None and not isinstance(clone_url, str)
    ):
        raise ForgeContractError(
            "Forge repository has invalid clone metadata",
            status_code=502,
            code="FORGE_CONTRACT_ERROR",
            body=payload,
        )
    if (
        clone_ready != (payload["state"] == "active")
        or (clone_ready and not clone_url)
        or (not clone_ready and clone_url is not None)
    ):
        raise ForgeContractError(
            "Forge repository clone readiness is inconsistent",
            status_code=502,
            code="FORGE_CONTRACT_ERROR",
            body=payload,
        )
    if not isinstance(project_ids, list) or not all(
        isinstance(value, str) for value in project_ids
    ):
        raise ForgeContractError(
            "Forge repository has invalid project_ids",
            status_code=502,
            code="FORGE_CONTRACT_ERROR",
            body=payload,
        )
    return cast(ForgeRepository, dict(payload))


def _data(payload: Any) -> Any:
    if not isinstance(payload, dict) or "data" not in payload:
        raise ForgeContractError(
            "Forge returned an invalid success envelope",
            status_code=502,
            code="FORGE_CONTRACT_ERROR",
            body=payload,
        )
    return payload["data"]


def _contract(condition: bool, message: str, payload: Any) -> None:
    if not condition:
        raise ForgeContractError(
            message, status_code=502, code="FORGE_CONTRACT_ERROR", body=payload
        )


def _named_ref(payload: Any) -> ForgeNamedRef:
    _contract(isinstance(payload, dict), "Forge returned an invalid repository ref", payload)
    _contract(isinstance(payload.get("name"), str), "Forge repository ref is missing name", payload)
    _contract(isinstance(payload.get("oid"), str), "Forge repository ref is missing oid", payload)
    return cast(ForgeNamedRef, dict(payload))


def _refs(payload: Any) -> ForgeRepositoryRefs:
    _contract(isinstance(payload, dict), "Forge returned invalid repository refs", payload)
    _contract(
        isinstance(payload.get("default_branch"), str),
        "Forge refs are missing default_branch",
        payload,
    )
    _contract(
        payload.get("head_oid") is None or isinstance(payload.get("head_oid"), str),
        "Forge refs have invalid head_oid",
        payload,
    )
    _contract(
        isinstance(payload.get("branches"), list) and isinstance(payload.get("tags"), list),
        "Forge refs have invalid collections",
        payload,
    )
    for branch in payload["branches"]:
        _named_ref(branch)
        _contract(
            isinstance(branch.get("is_default"), bool), "Forge branch is missing is_default", branch
        )
    for tag in payload["tags"]:
        _named_ref(tag)
    return cast(ForgeRepositoryRefs, dict(payload))


def _tree(payload: Any) -> ForgeRepositoryTree:
    _contract(isinstance(payload, dict), "Forge returned invalid repository tree", payload)
    for field in ("ref", "commit_oid", "path"):
        _contract(isinstance(payload.get(field), str), f"Forge tree is missing {field}", payload)
    _contract(
        isinstance(payload.get("entries"), list) and isinstance(payload.get("truncated"), bool),
        "Forge tree has invalid entries",
        payload,
    )
    for entry in payload["entries"]:
        _contract(
            isinstance(entry, dict) and entry.get("type") in {"blob", "tree"},
            "Forge tree entry has invalid type",
            entry,
        )
        for field in ("name", "path", "oid"):
            _contract(
                isinstance(entry.get(field), str), f"Forge tree entry is missing {field}", entry
            )
        size = entry.get("size")
        _contract(
            size is None or (isinstance(size, int) and not isinstance(size, bool) and size >= 0),
            "Forge tree entry has invalid size",
            entry,
        )
    return cast(ForgeRepositoryTree, dict(payload))


def _blob(payload: Any) -> ForgeRepositoryBlob:
    _contract(isinstance(payload, dict), "Forge returned invalid repository blob", payload)
    for field in ("ref", "commit_oid", "path", "oid", "content"):
        _contract(isinstance(payload.get(field), str), f"Forge blob is missing {field}", payload)
    _contract(
        payload.get("encoding") in {"utf-8", "base64"}, "Forge blob has invalid encoding", payload
    )
    size = payload.get("size")
    _contract(
        isinstance(size, int) and not isinstance(size, bool) and size >= 0,
        "Forge blob has invalid size",
        payload,
    )
    return cast(ForgeRepositoryBlob, dict(payload))


def _history(payload: Any) -> ForgeCommitHistory:
    _contract(isinstance(payload, dict), "Forge returned invalid commit history", payload)
    _contract(
        isinstance(payload.get("ref"), str) and isinstance(payload.get("path"), str),
        "Forge commit history is missing location",
        payload,
    )
    page = payload.get("page")
    _contract(
        isinstance(page, dict) and isinstance(page.get("has_more"), bool),
        "Forge commit history has invalid pagination",
        payload,
    )
    _contract(
        page.get("next_cursor") is None or isinstance(page.get("next_cursor"), str),
        "Forge commit history has invalid cursor",
        payload,
    )
    _contract(
        isinstance(payload.get("commits"), list),
        "Forge commit history has invalid commits",
        payload,
    )
    fields = (
        "oid",
        "short_oid",
        "subject",
        "author_name",
        "author_email",
        "authored_at",
        "committer_name",
        "committed_at",
    )
    for commit in payload["commits"]:
        _contract(isinstance(commit, dict), "Forge commit is invalid", commit)
        for field in fields:
            _contract(
                isinstance(commit.get(field), str), f"Forge commit is missing {field}", commit
            )
        _contract(
            isinstance(commit.get("parents"), list)
            and all(isinstance(parent, str) for parent in commit["parents"]),
            "Forge commit has invalid parents",
            commit,
        )
    return cast(ForgeCommitHistory, dict(payload))


def _content_params(
    ref: str | None = None, path: str | None = None, **values: Any
) -> dict[str, Any] | None:
    params = {"ref": ref, "path": path, **values}
    compacted = {key: value for key, value in params.items() if value is not None}
    return compacted or None


def _create_body(
    name: str,
    slug: str | None,
    default_branch: str | None,
    visibility: ForgeRepositoryVisibility | None,
    project_ids: list[str] | None,
) -> dict[str, Any]:
    values = {
        "name": name,
        "slug": slug,
        "default_branch": default_branch,
        "visibility": visibility,
        "project_ids": project_ids,
    }
    return {key: value for key, value in values.items() if value is not None}


def _headers(idempotency_key: str | None) -> dict[str, str] | None:
    return {"Idempotency-Key": idempotency_key} if idempotency_key else None


def _translate_error(error: MiosaError) -> NoReturn:
    if error.code == "FORGE_DISABLED":
        raise ForgeUnavailableError(
            "Forge is not enabled for this organization",
            status_code=error.status_code,
            code="FORGE_DISABLED",
            body=error.body,
            request_id=error.request_id,
        ) from error
    if error.code in {"FORGE_STORAGE_UNAVAILABLE", "FORGE_OPERATION_FAILED"}:
        raise ForgeStorageError(
            "Forge repository storage is unavailable",
            status_code=error.status_code,
            code=error.code,
            body=error.body,
            request_id=error.request_id,
        ) from error
    if error.code == "INVALID_PROJECT_ATTACHMENT":
        raise ForgePolicyViolationError(
            "Forge repository policy rejected the operation",
            status_code=error.status_code,
            code=error.code,
            body=error.body,
            request_id=error.request_id,
        ) from error
    raise error


class ForgeRepositories:
    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def create(
        self,
        name: str,
        *,
        slug: str | None = None,
        default_branch: str | None = None,
        visibility: ForgeRepositoryVisibility | None = None,
        project_ids: builtins.list[str] | None = None,
        idempotency_key: str | None = None,
    ) -> ForgeRepository:
        try:
            payload = self._transport.request(
                "POST",
                _REPOSITORIES,
                json_body=_create_body(name, slug, default_branch, visibility, project_ids),
                headers=_headers(idempotency_key or str(uuid4())),
            )
        except MiosaError as error:
            _translate_error(error)
        return _repository(_data(payload))

    def list(self) -> builtins.list[ForgeRepository]:
        payload = self._transport.request(
            "GET",
            _REPOSITORIES,
            params=None,
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ForgeContractError(
                "Forge returned an invalid repository list",
                status_code=502,
                code="FORGE_CONTRACT_ERROR",
                body=payload,
            )
        return [_repository(item) for item in payload["data"]]

    def get(self, repository_id: str) -> ForgeRepository:
        return _repository(_data(self._transport.request("GET", _repository_path(repository_id))))

    def refs(self, repository_id: str) -> ForgeRepositoryRefs:
        payload = self._transport.request("GET", f"{_repository_path(repository_id)}/refs")
        return _refs(_data(payload))

    def tree(
        self, repository_id: str, *, ref: str | None = None, path: str | None = None
    ) -> ForgeRepositoryTree:
        payload = self._transport.request(
            "GET", f"{_repository_path(repository_id)}/tree", params=_content_params(ref, path)
        )
        return _tree(_data(payload))

    def blob(self, repository_id: str, path: str, *, ref: str | None = None) -> ForgeRepositoryBlob:
        payload = self._transport.request(
            "GET", f"{_repository_path(repository_id)}/blob", params=_content_params(ref, path)
        )
        return _blob(_data(payload))

    def readme(
        self, repository_id: str, *, ref: str | None = None, path: str | None = None
    ) -> ForgeRepositoryBlob:
        payload = self._transport.request(
            "GET", f"{_repository_path(repository_id)}/readme", params=_content_params(ref, path)
        )
        return _blob(_data(payload))

    def commits(
        self,
        repository_id: str,
        *,
        ref: str | None = None,
        path: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> ForgeCommitHistory:
        payload = self._transport.request(
            "GET",
            f"{_repository_path(repository_id)}/commits",
            params=_content_params(ref, path, limit=limit, cursor=cursor),
        )
        return _history(_data(payload))

    def update(
        self,
        repository_id: str,
        *,
        name: str | None = None,
        slug: str | None = None,
        visibility: ForgeRepositoryVisibility | None = None,
        project_ids: builtins.list[str] | None = None,
    ) -> ForgeRepository:
        body = {
            key: value
            for key, value in {
                "name": name,
                "slug": slug,
                "visibility": visibility,
                "project_ids": project_ids,
            }.items()
            if value is not None
        }
        try:
            return _repository(
                _data(
                    self._transport.request(
                        "PATCH", _repository_path(repository_id), json_body=body
                    )
                )
            )
        except MiosaError as error:
            _translate_error(error)

    def delete(self, repository_id: str) -> dict[str, Any]:
        try:
            payload = self._transport.request(
                "DELETE",
                _repository_path(repository_id),
                raw_response=True,
            )
        except MiosaError as error:
            _translate_error(error)
        operation_id = payload.headers.get("x-forge-operation-id")
        if not operation_id:
            raise ForgeContractError(
                "Forge delete omitted its operation receipt",
                status_code=502,
                code="FORGE_CONTRACT_ERROR",
            )
        return {
            "operation_id": operation_id,
            "replayed": payload.headers.get("idempotency-replayed") == "true",
        }


class Forge:
    def __init__(self, transport: SyncTransport) -> None:
        self.repositories = ForgeRepositories(transport)


class AsyncForgeRepositories:
    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def create(
        self,
        name: str,
        *,
        slug: str | None = None,
        default_branch: str | None = None,
        visibility: ForgeRepositoryVisibility | None = None,
        project_ids: builtins.list[str] | None = None,
        idempotency_key: str | None = None,
    ) -> ForgeRepository:
        try:
            payload = await self._transport.request(
                "POST",
                _REPOSITORIES,
                json_body=_create_body(name, slug, default_branch, visibility, project_ids),
                headers=_headers(idempotency_key or str(uuid4())),
            )
        except MiosaError as error:
            _translate_error(error)
        return _repository(_data(payload))

    async def list(self) -> builtins.list[ForgeRepository]:
        payload = await self._transport.request(
            "GET",
            _REPOSITORIES,
            params=None,
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ForgeContractError(
                "Forge returned an invalid repository list",
                status_code=502,
                code="FORGE_CONTRACT_ERROR",
                body=payload,
            )
        return [_repository(item) for item in payload["data"]]

    async def get(self, repository_id: str) -> ForgeRepository:
        payload = await self._transport.request("GET", _repository_path(repository_id))
        return _repository(_data(payload))

    async def refs(self, repository_id: str) -> ForgeRepositoryRefs:
        payload = await self._transport.request("GET", f"{_repository_path(repository_id)}/refs")
        return _refs(_data(payload))

    async def tree(
        self, repository_id: str, *, ref: str | None = None, path: str | None = None
    ) -> ForgeRepositoryTree:
        payload = await self._transport.request(
            "GET", f"{_repository_path(repository_id)}/tree", params=_content_params(ref, path)
        )
        return _tree(_data(payload))

    async def blob(
        self, repository_id: str, path: str, *, ref: str | None = None
    ) -> ForgeRepositoryBlob:
        payload = await self._transport.request(
            "GET", f"{_repository_path(repository_id)}/blob", params=_content_params(ref, path)
        )
        return _blob(_data(payload))

    async def readme(
        self, repository_id: str, *, ref: str | None = None, path: str | None = None
    ) -> ForgeRepositoryBlob:
        payload = await self._transport.request(
            "GET", f"{_repository_path(repository_id)}/readme", params=_content_params(ref, path)
        )
        return _blob(_data(payload))

    async def commits(
        self,
        repository_id: str,
        *,
        ref: str | None = None,
        path: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> ForgeCommitHistory:
        payload = await self._transport.request(
            "GET",
            f"{_repository_path(repository_id)}/commits",
            params=_content_params(ref, path, limit=limit, cursor=cursor),
        )
        return _history(_data(payload))

    async def update(
        self,
        repository_id: str,
        *,
        name: str | None = None,
        slug: str | None = None,
        visibility: ForgeRepositoryVisibility | None = None,
        project_ids: builtins.list[str] | None = None,
    ) -> ForgeRepository:
        body = {
            key: value
            for key, value in {
                "name": name,
                "slug": slug,
                "visibility": visibility,
                "project_ids": project_ids,
            }.items()
            if value is not None
        }
        try:
            payload = await self._transport.request(
                "PATCH", _repository_path(repository_id), json_body=body
            )
            return _repository(_data(payload))
        except MiosaError as error:
            _translate_error(error)

    async def delete(self, repository_id: str) -> dict[str, Any]:
        try:
            payload = await self._transport.request(
                "DELETE",
                _repository_path(repository_id),
                raw_response=True,
            )
        except MiosaError as error:
            _translate_error(error)
        operation_id = payload.headers.get("x-forge-operation-id")
        if not operation_id:
            raise ForgeContractError(
                "Forge delete omitted its operation receipt",
                status_code=502,
                code="FORGE_CONTRACT_ERROR",
            )
        return {
            "operation_id": operation_id,
            "replayed": payload.headers.get("idempotency-replayed") == "true",
        }


class AsyncForge:
    def __init__(self, transport: AsyncTransport) -> None:
        self.repositories = AsyncForgeRepositories(transport)


__all__ = [
    "AsyncForge",
    "AsyncForgeRepositories",
    "Forge",
    "ForgeContractError",
    "ForgePolicyViolationError",
    "ForgeRepositoryBlob",
    "ForgeRepositoryRefs",
    "ForgeRepositoryTree",
    "ForgeCommitHistory",
    "ForgeRepositories",
    "ForgeRepository",
    "ForgeRepositoryState",
    "ForgeRepositoryVisibility",
    "ForgeStorageError",
    "ForgeUnavailableError",
]
