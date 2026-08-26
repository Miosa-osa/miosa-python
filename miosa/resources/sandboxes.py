"""Native Sandbox resource backed only by ``/sandboxes``.

Sandboxes are lightweight Firecracker Linux environments for code execution,
artifacts, and previews. Every operation in this module stays on the sandbox
API surface.
"""

from __future__ import annotations

import base64
import contextlib
import json
import logging
import time
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Any, Literal, TypedDict, cast
from urllib.parse import quote, urlencode, urlparse, urlunparse

import httpx

from ..errors import MiosaError, NotFoundError, raise_for_status
from .connectors import AsyncSandboxConnectors, SandboxConnectors
from .egress_audit import AsyncSandboxAudit, SandboxAudit
from .egress_network import AsyncSandboxNetwork, SandboxNetwork
from .egress_secrets import AsyncSandboxSecrets, SandboxSecrets
from .sandbox_namespaces import (
    AsyncSandboxArtifactsResource,
    AsyncSandboxCommands,
    AsyncSandboxEnv,
    AsyncSandboxEvents,
    AsyncSandboxExecRunner,
    AsyncSandboxFiles,
    AsyncSandboxGit,
    AsyncSandboxLogs,
    AsyncSandboxPreview,
    AsyncSandboxProcesses,
    AsyncSandboxShare,
    AsyncSandboxSnapshots,
    AsyncSandboxTags,
    AsyncSandboxTerminal,
    SandboxArtifactsResource,
    SandboxCommands,
    SandboxEnv,
    SandboxEvents,
    SandboxExecRunner,
    SandboxFiles,
    SandboxGit,
    SandboxLogs,
    SandboxPreview,
    SandboxProcesses,
    SandboxShare,
    SandboxSnapshots,
    SandboxTags,
    SandboxTerminal,
)

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


_LOGGER = logging.getLogger(__name__)

DEFAULT_TEMPLATE = "miosa-sandbox"
AGENT_WORKSPACE_TIMEOUT_SEC = 86_400
AGENT_WORKSPACE_IDLE_TIMEOUT_SEC = 1_800
AGENT_WORKSPACE_SNAPSHOT_EXPIRATION_SEC = 30 * 86_400
AGENT_WORKSPACE_KEEP_LAST_SNAPSHOTS = 1
SandboxState = Literal["provisioning", "running", "paused", "destroyed", "error"]
SandboxSize = Literal["xs", "small", "medium", "large", "xl"]
SANDBOX_SHAPE_CONTRACTS: dict[SandboxSize, tuple[int, int, int]] = {
    "xs": (1, 2_048, 10_240),
    "small": (2, 4_096, 10_240),
    "medium": (4, 8_192, 20_480),
    "large": (8, 16_384, 40_960),
    "xl": (16, 32_768, 81_920),
}


def _normalize_preview_url(url: str | None) -> str | None:
    """Normalize legacy duplicated sandbox preview hostnames."""
    if not url:
        return url
    return url.replace(".sandbox.sandbox.preview.", ".sandbox.preview.")


def _normalize_preview_info(data: dict[str, Any]) -> dict[str, Any]:
    embedded = data.get("url_info")
    if isinstance(embedded, dict):
        merged = {**embedded, **data}
    else:
        merged = dict(data)
    merged["url"] = _normalize_preview_url(cast(str | None, merged.get("url"))) or ""
    url_class = str(merged.get("url_class") or merged.get("class") or "temporary_preview")
    merged["url_class"] = url_class
    merged["class"] = url_class
    merged["stable_for_embedding"] = bool(merged.get("stable_for_embedding", False))
    merged["recommended_next_action"] = str(
        merged.get("recommended_next_action") or "create_alias_or_publish"
    )
    return merged


class CreateSandboxOptions(TypedDict, total=False):
    template_id: str
    image: str
    size: SandboxSize
    cpu_count: int
    memory_mb: int
    disk_mb: int
    disk_size_mb: int
    timeout_sec: int
    env: dict[str, str]
    metadata: dict[str, Any]
    services: list[dict[str, Any]]
    readiness_probe: dict[str, Any]
    database: dict[str, Any] | bool
    github_repo_url: str
    github_branch: str
    github_clone_path: str
    name: str
    region: str
    idle_timeout_sec: int
    persistent: bool
    snapshot_expiration_sec: int
    snapshot_expiration_days: int
    keep_last_snapshots: int | dict[str, Any]
    always_on: bool
    # Opt in to the in-sandbox L3 token carrying the ``provision`` scope, so
    # code running inside the sandbox can call database/deployment create.
    # Defaults to false on the server when omitted.
    allow_provision: bool
    entrypoint: str
    tags: list[str]
    idempotency_key: str
    slug: str
    agent_runtime_profile_id: str
    agent_profile_id: str
    skip_agent_runtime_profile: bool
    # Canonical MIOSA workspace and project ownership selectors.
    workspace_id: str
    workspace_slug: str
    workspace_name: str
    project_id: str
    project_slug: str
    project_name: str
    # White-label attribution. See miosa.types.ExternalAttribution.
    external_workspace_id: str
    external_user_id: str
    external_project_id: str


class SandboxUsage(TypedDict):
    sandbox_id: str
    state: str
    runtime_sec: int
    provisioned_vcpu_ms: int
    provisioned_memory_mb_ms: int | None
    creation_count: int
    active_cpu_ms: int | None
    network_ingress_bytes: int | None
    network_egress_bytes: int | None
    measurement_status: dict[str, str]
    estimated_cost_cents: int
    timeout_sec: int
    timeout_remaining_ms: int | None


class ExecOptions(TypedDict, total=False):
    cwd: str
    working_dir: str
    env: dict[str, str]
    timeout_sec: int
    timeout: int


class StartTemplateOptions(TypedDict, total=False):
    install: bool
    install_command: str
    start_command: str
    install_timeout_sec: int
    start_timeout_sec: int
    port: int
    workdir: str
    readiness_probe: dict[str, Any]


@dataclass
class ExecResult:
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int

    @property
    def output(self) -> str:
        """Alias for ``stdout``, for compatibility with computer ``ExecResult``."""
        return self.stdout


@dataclass(slots=True)
class SandboxEvent:
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    id: str | None = None


@dataclass(slots=True)
class PreviewUrlInfo:
    data: dict[str, Any]

    @property
    def url(self) -> str:
        return str(self.data.get("url") or self.data.get("preview_url") or "")

    @property
    def url_class(self) -> str:
        return str(self.data.get("url_class") or self.data.get("class") or "temporary_preview")

    @property
    def class_(self) -> str:
        return self.url_class

    @property
    def stable_for_embedding(self) -> bool:
        return bool(self.data.get("stable_for_embedding", False))

    @property
    def recommended_next_action(self) -> str:
        return str(self.data.get("recommended_next_action") or "create_alias_or_publish")


@dataclass(slots=True)
class TemplateLifecycleManifest:
    data: dict[str, Any]

    @property
    def preview_url(self) -> str | None:
        value = self.data.get("preview_url")
        return value if isinstance(value, str) else None


@dataclass(slots=True)
class SandboxArtifacts:
    data: dict[str, Any]

    @property
    def artifacts(self) -> dict[str, Any]:
        value = self.data.get("artifacts")
        return value if isinstance(value, dict) else {}

    @property
    def preview(self) -> dict[str, Any]:
        value = self.data.get("preview")
        return value if isinstance(value, dict) else {}


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _to_base64(content: bytes | str | Path) -> str:
    if isinstance(content, Path):
        return base64.b64encode(content.read_bytes()).decode("ascii")
    if isinstance(content, str):
        return base64.b64encode(content.encode("utf-8")).decode("ascii")
    return base64.b64encode(content).decode("ascii")


def _normalize_sandbox_payload(data: Any) -> dict[str, Any]:
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        return cast(dict[str, Any], data["data"])
    if isinstance(data, dict):
        return cast(dict[str, Any], data)
    raise TypeError("Expected sandbox response object")


def _unwrap_preview_token(data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        for k in ("data", "preview_token"):
            if k in data and isinstance(data[k], dict):
                return cast(dict[str, Any], data[k])
    return cast(dict[str, Any], data) if isinstance(data, dict) else {}


def _normalize_list_payload(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return cast(list[dict[str, Any]], data)
    if isinstance(data, dict):
        for key in ("sandboxes", "data", "items"):
            items = data.get(key)
            if isinstance(items, list):
                return cast(list[dict[str, Any]], items)
    return []


def _resolve_create_size(options: CreateSandboxOptions) -> SandboxSize | None:
    disk_size_mb = options.get("disk_size_mb", options.get("disk_mb"))
    exact_resources = (options.get("cpu_count"), options.get("memory_mb"), disk_size_mb)
    supplied_resource_count = sum(value is not None for value in exact_resources)
    requested_size = options.get("size")

    if supplied_resource_count == 0:
        return requested_size
    if supplied_resource_count != 3:
        raise TypeError(
            "Raw sandbox resources require cpu_count, memory_mb, and disk_size_mb together. "
            "Prefer size."
        )

    requested = cast(tuple[int, int, int], exact_resources)
    matching_size = next(
        (name for name, contract in SANDBOX_SHAPE_CONTRACTS.items() if contract == requested),
        None,
    )
    if matching_size is None:
        raise ValueError("Raw sandbox resources must exactly match a named size contract.")
    if requested_size is not None and requested_size != matching_size:
        raise ValueError(
            f"Raw sandbox resources match {matching_size}, not requested size {requested_size}."
        )
    return matching_size


def _build_create_body(options: CreateSandboxOptions) -> dict[str, Any]:
    template_id = options.get("template_id") or options.get("image") or DEFAULT_TEMPLATE
    metadata = dict(options.get("metadata") or {})
    persistent = options.get("persistent")
    legacy_persistence_policy = persistent is not None and (
        "snapshot_expiration_sec" in options
        or "snapshot_expiration_days" in options
        or "keep_last_snapshots" in options
    )
    if legacy_persistence_policy:
        metadata["miosa_persistent"] = persistent
    if "snapshot_expiration_sec" in options:
        metadata["snapshot_expiration_sec"] = options["snapshot_expiration_sec"]
    elif "snapshot_expiration_days" in options:
        metadata["snapshot_expiration_sec"] = int(options["snapshot_expiration_days"]) * 86_400
    if "keep_last_snapshots" in options:
        metadata["keep_last_snapshots"] = options["keep_last_snapshots"]

    body: dict[str, Any] = {"template_id": template_id}
    resolved_size = _resolve_create_size(options)
    if resolved_size is not None:
        body["size"] = resolved_size
    if persistent is not None:
        body["persistent"] = persistent
    if legacy_persistence_policy and persistent is True:
        body["timeout_sec"] = options.get("timeout_sec", AGENT_WORKSPACE_TIMEOUT_SEC)
        body["idle_timeout_sec"] = options.get(
            "idle_timeout_sec", AGENT_WORKSPACE_IDLE_TIMEOUT_SEC
        )
    for key in (
        "cpu_count",
        "memory_mb",
        "disk_mb",
        "disk_size_mb",
        "timeout_sec",
        "env",
        "services",
        "readiness_probe",
        "database",
        "github_repo_url",
        "github_branch",
        "github_clone_path",
        "name",
        "region",
        "idle_timeout_sec",
        "always_on",
        "allow_provision",
        "entrypoint",
        "tags",
        "slug",
        "agent_runtime_profile_id",
        "agent_profile_id",
        "skip_agent_runtime_profile",
        "workspace_id",
        "workspace_slug",
        "workspace_name",
        "project_id",
        "project_slug",
        "project_name",
        # White-label attribution. Backend stores these as text on the
        # sandbox row (Engine.ExternalAttribution).
        "external_workspace_id",
        "external_user_id",
        "external_project_id",
    ):
        if key in options:
            body[key] = options[key]
    if metadata:
        body["metadata"] = metadata
    return body


def _merge_create_options(
    template_id: str | None,
    image: str | None,
    size: SandboxSize | None,
    cpu_count: int | None,
    memory_mb: int | None,
    disk_mb: int | None,
    disk_size_mb: int | None,
    timeout_sec: int | None,
    env: dict[str, str] | None,
    metadata: dict[str, Any] | None,
    services: list[dict[str, Any]] | None,
    readiness_probe: dict[str, Any] | None,
    database: dict[str, Any] | bool | None,
    github_repo_url: str | None,
    github_branch: str | None,
    github_clone_path: str | None,
    name: str | None,
    region: str | None,
    idle_timeout_sec: int | None,
    persistent: bool | None,
    snapshot_expiration_sec: int | None,
    snapshot_expiration_days: int | None,
    keep_last_snapshots: int | dict[str, Any] | None,
    always_on: bool | None,
    entrypoint: str | None,
    tags: list[str] | None,
    idempotency_key: str | None,
    opts: CreateSandboxOptions | None,
    workspace_id: str | None = None,
    workspace_slug: str | None = None,
    workspace_name: str | None = None,
    project_id: str | None = None,
    project_slug: str | None = None,
    project_name: str | None = None,
    external_workspace_id: str | None = None,
    external_user_id: str | None = None,
    external_project_id: str | None = None,
    slug: str | None = None,
    agent_runtime_profile_id: str | None = None,
    agent_profile_id: str | None = None,
    skip_agent_runtime_profile: bool | None = None,
    allow_provision: bool | None = None,
) -> CreateSandboxOptions:
    if opts is not None:
        if template_id is not None or image is not None or size is not None:
            raise TypeError("Pass either `opts` or individual create arguments, not both.")
        # Allow attribution to merge in even when `opts` is supplied so
        # white-label callers can pass a static opts dict and still tag
        # per-request with external IDs.
        merged_opts: CreateSandboxOptions = dict(opts)  # type: ignore[assignment]
        for key, value in (
            ("workspace_id", workspace_id),
            ("workspace_slug", workspace_slug),
            ("workspace_name", workspace_name),
            ("project_id", project_id),
            ("project_slug", project_slug),
            ("project_name", project_name),
            ("external_workspace_id", external_workspace_id),
            ("external_user_id", external_user_id),
            ("external_project_id", external_project_id),
            ("slug", slug),
            ("size", size),
            ("persistent", persistent),
            ("snapshot_expiration_sec", snapshot_expiration_sec),
            ("snapshot_expiration_days", snapshot_expiration_days),
            ("keep_last_snapshots", keep_last_snapshots),
            ("agent_runtime_profile_id", agent_runtime_profile_id),
            ("agent_profile_id", agent_profile_id),
            ("skip_agent_runtime_profile", skip_agent_runtime_profile),
            ("allow_provision", allow_provision),
        ):
            if value is not None:
                merged_opts[key] = value  # type: ignore[literal-required]
        return merged_opts
    if image is not None:
        if template_id is not None:
            raise TypeError("Pass either `image` or `template_id`, not both.")
        template_id = image

    merged: CreateSandboxOptions = {"template_id": template_id or DEFAULT_TEMPLATE}
    if size is not None:
        merged["size"] = size
    values: dict[str, Any] = {
        "cpu_count": cpu_count,
        "memory_mb": memory_mb,
        "disk_mb": disk_mb,
        "disk_size_mb": disk_size_mb,
        "timeout_sec": timeout_sec,
        "env": env,
        "metadata": metadata,
        "services": services,
        "readiness_probe": readiness_probe,
        "database": database,
        "github_repo_url": github_repo_url,
        "github_branch": github_branch,
        "github_clone_path": github_clone_path,
        "name": name,
        "region": region,
        "idle_timeout_sec": idle_timeout_sec,
        "persistent": persistent,
        "snapshot_expiration_sec": snapshot_expiration_sec,
        "snapshot_expiration_days": snapshot_expiration_days,
        "keep_last_snapshots": keep_last_snapshots,
        "always_on": always_on,
        "entrypoint": entrypoint,
        "tags": tags,
        "idempotency_key": idempotency_key,
        "workspace_id": workspace_id,
        "workspace_slug": workspace_slug,
        "workspace_name": workspace_name,
        "project_id": project_id,
        "project_slug": project_slug,
        "project_name": project_name,
        "external_workspace_id": external_workspace_id,
        "external_user_id": external_user_id,
        "external_project_id": external_project_id,
        "slug": slug,
        "agent_runtime_profile_id": agent_runtime_profile_id,
        "agent_profile_id": agent_profile_id,
        "skip_agent_runtime_profile": skip_agent_runtime_profile,
        "allow_provision": allow_provision,
    }
    for key, value in values.items():
        if value is not None:
            merged[key] = value  # type: ignore[literal-required]
    return merged


def _exec_payload(command: str, opts: ExecOptions | None) -> dict[str, Any]:
    body: dict[str, Any] = {"command": command}
    if opts is None:
        return body
    if "cwd" in opts:
        body["cwd"] = opts["cwd"]
    if "working_dir" in opts:
        body["cwd"] = opts["working_dir"]
    if "env" in opts:
        body["env"] = opts["env"]
    if "timeout" in opts:
        body["timeout"] = opts["timeout"]
    if "timeout_sec" in opts:
        body["timeout"] = opts["timeout_sec"]
    return body


def _template_start_payload(opts: StartTemplateOptions | None) -> dict[str, Any]:
    return dict(opts or {})


def _read_result_data(response: Any) -> dict[str, Any]:
    if isinstance(response, dict) and isinstance(response.get("data"), dict):
        return cast(dict[str, Any], response["data"])
    if isinstance(response, dict):
        return cast(dict[str, Any], response)
    return {}


def _report_surviving_release(
    error: BaseException, release_id: str, cleanup_error: Exception | None
) -> None:
    if cleanup_error is None:
        message = (
            f"release sandbox {release_id} is still running because cleanup was disabled"
        )
    else:
        message = (
            f"release sandbox {release_id} was not destroyed and is still billable: "
            f"{cleanup_error}"
        )
        _LOGGER.warning(message)
    add_note = getattr(error, "add_note", None)
    if callable(add_note):
        add_note(message)


class Sandbox:
    """Bound sync handle for one native MIOSA sandbox."""

    def __init__(self, transport: SyncTransport, data: dict[str, Any]) -> None:
        self._transport = transport
        self.exec = SandboxExecRunner(self)
        self.commands = SandboxCommands(self)
        self.files = SandboxFiles(self)
        self.git = SandboxGit(self)
        self.preview = SandboxPreview(self)
        self.previews = self.preview  # alias for plural-noun ergonomics
        self.artifacts = SandboxArtifactsResource(self)
        self.logs = SandboxLogs(self)
        self.snapshots = SandboxSnapshots(self)
        self.events = SandboxEvents(self)
        self.env = SandboxEnv(self)
        self.terminal = SandboxTerminal(self)
        self.tags = SandboxTags(self)
        self.processes = SandboxProcesses(self)
        self.share = SandboxShare(self)
        # Egress (security) namespaces — pre-scoped to this sandbox id
        sandbox_id = str(data["id"])
        self.connectors = SandboxConnectors(transport, sandbox_id)
        self.secrets = SandboxSecrets(transport, sandbox_id)
        self.network = SandboxNetwork(transport, sandbox_id)
        self.audit = SandboxAudit(transport, sandbox_id)
        self._replace(data)

    def _replace(self, data: dict[str, Any]) -> None:
        self.data = data
        self.id = str(data["id"])
        self.state = cast(SandboxState, data.get("state", "provisioning"))
        self.ready = bool(data.get("ready", self.state == "running"))
        self.template_id = str(data.get("template_id") or data.get("image_id") or "")
        self.tenant_id = cast(str | None, data.get("tenant_id"))
        self.owner_id = cast(str | None, data.get("owner_id"))
        self.workspace_id = cast(str | None, data.get("workspace_id"))
        self.workspace_slug = cast(str | None, data.get("workspace_slug"))
        self.workspace_name = cast(str | None, data.get("workspace_name"))
        self.project_id = cast(str | None, data.get("project_id"))
        self.project_slug = cast(str | None, data.get("project_slug"))
        self.project_name = cast(str | None, data.get("project_name"))
        self.external_workspace_id = cast(str | None, data.get("external_workspace_id"))
        self.external_user_id = cast(str | None, data.get("external_user_id"))
        self.external_project_id = cast(str | None, data.get("external_project_id"))
        self.size = cast(SandboxSize | None, data.get("size"))
        self.resource_contract = cast(dict[str, Any] | None, data.get("resource_contract"))
        self.image_id = cast(str | None, data.get("image_id"))
        self.cpu_count = cast(int | None, data.get("cpu_count"))
        self.memory_mb = cast(int | None, data.get("memory_mb"))
        self.disk_size_mb = cast(int | None, data.get("disk_size_mb") or data.get("disk_mb"))
        self.timeout_sec = cast(int | None, data.get("timeout_sec"))
        self.timeout_remaining_ms = cast(int | None, data.get("timeout_remaining_ms"))
        self.idle_timeout_sec = cast(int | None, data.get("idle_timeout_sec"))
        self.always_on = bool(data.get("always_on", False))
        self.persistent = bool(data.get("persistent", False))
        self.slug = cast(str | None, data.get("slug"))
        self.name = cast(str | None, data.get("name"))
        self.metadata = cast(dict[str, Any], data.get("metadata") or {})
        self.preview_url = cast(str | None, data.get("preview_url"))
        self.url_info = cast(dict[str, Any] | None, data.get("url_info"))
        self.url_class = cast(str | None, data.get("url_class"))
        self.stable_for_embedding = cast(bool | None, data.get("stable_for_embedding"))
        self.recommended_next_action = cast(str | None, data.get("recommended_next_action"))
        self.preview_domain = cast(str | None, data.get("preview_domain"))
        self.boot_path = cast(str | None, data.get("boot_path"))
        self.boot_ms = cast(int | None, data.get("boot_ms"))
        self.created_at = _parse_iso(data.get("created_at") or data.get("inserted_at"))
        self.started_at = _parse_iso(data.get("started_at"))
        self.ready_at = _parse_iso(data.get("ready_at"))
        self.destroyed_at = _parse_iso(data.get("destroyed_at"))
        self.total_runtime_sec = cast(int | None, data.get("total_runtime_sec"))

    def __enter__(self) -> Sandbox:
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        if self.state != "destroyed":
            with contextlib.suppress(Exception):
                self.destroy()

    def __repr__(self) -> str:
        return f"Sandbox(id={self.id!r}, state={self.state!r}, template_id={self.template_id!r})"

    def refresh(self) -> Sandbox:
        data = self._transport.request("GET", f"/sandboxes/{self.id}")
        self._replace(_normalize_sandbox_payload(data))
        return self

    def run_agent(
        self,
        instruction: str,
        *,
        runner: str = "claude-code",
        provider: str | None = None,
        model: str | None = None,
        cwd: str = "/workspace",
        timeout: int | None = None,
        wait: bool = True,
        env: dict[str, str] | None = None,
        output_format: str | None = None,
        resume_session_id: str | None = None,
        json: bool | None = None,
        output_schema: str | None = None,
        image: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Run an AI coding agent inside this Sandbox."""
        body = {
            "instruction": instruction,
            "target_kind": "sandbox",
            "target_id": self.id,
            "runtime_id": self.id,
            "sandbox_id": self.id,
            "runner": runner,
            "provider": provider,
            "model": model,
            "cwd": cwd,
            "timeout": timeout,
            "wait": wait,
            "env": env,
            "output_format": output_format,
            "resume_session_id": resume_session_id,
            "json": json,
            "output_schema": output_schema,
            "image": image,
            **kwargs,
        }
        body = {key: value for key, value in body.items() if value is not None}
        return cast(
            dict[str, Any],
            _read_result_data(
                self._transport.request("POST", "/runs", json_body=body)
            ),
        )

    def prompt(
        self,
        prompt: str,
        *,
        provider: str | None = "claude",
        model: str | None = None,
        cwd: str = "/workspace",
        timeout: int | None = None,
        wait: bool = True,
        env: dict[str, str] | None = None,
        output_format: str | None = None,
        resume_session_id: str | None = None,
        json: bool | None = None,
        output_schema: str | None = None,
        image: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Dispatch a prompt into this Sandbox through the Agent Runs API."""
        body = {
            "prompt": prompt,
            "target_kind": "sandbox",
            "target_id": self.id,
            "sandbox_id": self.id,
            "provider": provider,
            "model": model,
            "cwd": cwd,
            "timeout": timeout,
            "wait": wait,
            "env": env,
            "output_format": output_format,
            "resume_session_id": resume_session_id,
            "json": json,
            "output_schema": output_schema,
            "image": image,
            **kwargs,
        }
        body = {key: value for key, value in body.items() if value is not None}
        return cast(
            dict[str, Any],
            _read_result_data(
                self._transport.request("POST", "/agent-runs", json_body=body)
            ),
        )

    def readiness(self) -> dict[str, Any]:
        """Return the sandbox readiness-probe state (``GET /readiness``)."""
        response = self._transport.request("GET", f"/sandboxes/{self.id}/readiness")
        return _read_result_data(response) if response else {}

    def wait_until_ready(self, timeout: float = 30.0, stream: bool = True) -> bool:
        """Block until the sandbox reports ready, or *timeout* seconds elapse.

        When ``stream=True`` (the default) this opens an SSE connection to
        ``GET /sandboxes/:id/readiness/stream`` and waits for an
        ``event: ready`` frame. The server emits ``ready`` immediately if
        the sandbox is already ready, otherwise as soon as the readiness
        PubSub message fires (typical < 1 s for warm-pool snapshots).

        Returns ``True`` once the sandbox is ready, ``False`` on
        ``event: timeout`` or when *timeout* elapses before ready.

        If the SSE endpoint returns 404 (server pre-dates the streaming
        endpoint) this transparently falls back to polling
        :meth:`readiness` every 10 ms until ready or timeout.
        """
        if stream:
            try:
                request = self._transport._client.build_request(
                    "GET",
                    f"/sandboxes/{self.id}/readiness/stream",
                    headers={"Accept": "text/event-stream"},
                    timeout=timeout + 5.0,
                )
                response = self._transport._client.send(request, stream=True)
                try:
                    if response.status_code == 404:
                        response.read()
                        # fall through to polling fallback below
                    elif not response.is_success:
                        body = response.read()
                        parsed: Any = body.decode("utf-8", errors="replace")
                        with contextlib.suppress(json.JSONDecodeError):
                            parsed = json.loads(parsed)
                        raise_for_status(
                            response.status_code,
                            parsed,
                            response.headers.get("x-request-id"),
                        )
                    else:
                        for raw_line in response.iter_lines():
                            line = (
                                raw_line
                                if isinstance(raw_line, str)
                                else raw_line.decode("utf-8", errors="replace")
                            )
                            if line.startswith("event: ready") or line.startswith("event:ready"):
                                return True
                            if line.startswith("event: timeout") or line.startswith(
                                "event:timeout"
                            ):
                                return False
                        # stream closed without a terminal event — fall through
                finally:
                    response.close()
            except (httpx.HTTPError, OSError):
                # SSE transport failed — fall through to polling fallback
                pass

        # Polling fallback (no exponential backoff — fixed 10 ms tick).
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                data = self.readiness()
            except MiosaError:
                data = {}
            if data.get("ready") or data.get("status") == "ready":
                return True
            time.sleep(0.01)
        return False

    def _run_exec(self, command: str, opts: ExecOptions | None = None) -> ExecResult:
        self._assert_running("exec")
        start_ms = time.monotonic()
        response = self._transport.request(
            "POST", f"/sandboxes/{self.id}/exec", json_body=_exec_payload(command, opts)
        )
        data = _read_result_data(response)
        return ExecResult(
            stdout=str(data.get("stdout", "")),
            stderr=str(data.get("stderr", "")),
            exit_code=int(data.get("exit_code", data.get("exitCode", 0))),
            duration_ms=int(data.get("duration_ms") or (time.monotonic() - start_ms) * 1000),
        )

    def exec_stream(self, command: str, opts: ExecOptions | None = None) -> Iterator[SandboxEvent]:
        self._assert_running("exec_stream")
        response = self._transport._client.build_request(
            "POST",
            f"/sandboxes/{self.id}/exec/stream",
            json=_exec_payload(command, opts),
            headers={"Accept": "text/event-stream"},
        )
        stream = self._transport._client.send(response, stream=True)
        try:
            if not stream.is_success:
                body = stream.read()
                parsed: Any = body.decode("utf-8", errors="replace")
                with contextlib.suppress(json.JSONDecodeError):
                    parsed = json.loads(parsed)
                raise_for_status(stream.status_code, parsed, stream.headers.get("x-request-id"))
            yield from _iter_sse(stream.iter_lines())
        finally:
            stream.close()

    def run(self, command: str, opts: ExecOptions | None = None) -> ExecResult:
        return self.exec.run(command, opts)

    def write_file(self, path: str, content: bytes | str | Path) -> None:
        self.upload(path, content)

    def upload(self, path: str, content: bytes | str | Path) -> None:
        self._assert_running("upload")
        self._transport.request(
            "POST",
            f"/sandboxes/{self.id}/files",
            json_body={"path": path, "content": _to_base64(content)},
        )

    def download(self, path: str) -> bytes:
        self._assert_running("download")
        response = self._transport.request(
            "GET", f"/sandboxes/{self.id}/files/{path.lstrip('/')}", raw_response=True
        )
        body: bytes = response.content
        content_type = response.headers.get("content-type", "")
        raise_for_status(response.status_code, response.text, response.headers.get("x-request-id"))
        if "application/json" not in content_type:
            return body
        parsed = response.json()
        data = _read_result_data(parsed)
        content = data.get("content", "")
        if isinstance(content, str):
            with contextlib.suppress(ValueError, TypeError):
                return base64.b64decode(content)
            return content.encode("utf-8")
        return b""

    def create_export(
        self,
        paths: str | list[str],
        *,
        label: str | None = None,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """Create a portable export descriptor for sandbox-generated files."""
        body: dict[str, Any] = {"path": paths} if isinstance(paths, str) else {"paths": paths}
        if label is not None:
            body["label"] = label
        if filename is not None:
            body["filename"] = filename
        response = self._transport.request(
            "POST", f"/sandboxes/{self.id}/exports", json_body=body
        )
        return _read_result_data(response)

    def download_export(self, paths: str | list[str], *, filename: str | None = None) -> bytes:
        """Download one exported file or a tar.gz archive for multiple paths."""
        query_items: list[tuple[str, str]] = []
        if isinstance(paths, str):
            query_items.append(("path", paths))
        else:
            query_items.extend(("paths[]", path) for path in paths)
        if filename is not None:
            query_items.append(("filename", filename))
        query = urlencode(query_items)
        response = self._transport.request(
            "GET", f"/sandboxes/{self.id}/exports/download?{query}", raw_response=True
        )
        raise_for_status(response.status_code, response.text, response.headers.get("x-request-id"))
        return cast(bytes, response.content)

    def read_file(self, path: str, *, text: bool = True) -> str | bytes:
        data = self.download(path)
        return data.decode("utf-8") if text else data

    def list_files(self, path: str = "/workspace", *, depth: int | None = None) -> dict[str, Any]:
        self._assert_running("files.list")
        params: dict[str, Any] = {"path": path}
        if depth is not None:
            params["depth"] = depth
        response = self._transport.request(
            "GET", f"/sandboxes/{self.id}/files", params=params
        )
        return _read_result_data(response)

    def stat_file(self, path: str) -> dict[str, Any]:
        self._assert_running("files.stat")
        response = self._transport.request(
            "POST", f"/sandboxes/{self.id}/files/stat", json_body={"path": path}
        )
        return _read_result_data(response)

    def expose(self, port: int | None = None) -> str:
        return self.expose_info(port).url

    def get_url(self, port: int | None = None, path: str = "/") -> str:
        parsed = urlparse(self.expose_info(port).url)
        normalized_path = path if path.startswith("/") else f"/{path}"
        return urlunparse(parsed._replace(path=normalized_path))

    def get_host(self, port: int | None = None) -> str:
        return urlparse(self.expose_info(port).url).netloc

    def expose_info(self, port: int | None = None) -> PreviewUrlInfo:
        self._assert_running("expose")
        response = self._transport.request(
            "POST",
            f"/sandboxes/{self.id}/expose",
            json_body={} if port is None else {"port": port},
        )
        data = _read_result_data(response)
        url = cast(str | None, data.get("url") or data.get("preview_url") or response.get("url"))
        merged = dict(data)
        merged["url"] = cast(str, _normalize_preview_url(url))
        return PreviewUrlInfo(_normalize_preview_info(merged))

    def start_template(self, opts: StartTemplateOptions | None = None) -> TemplateLifecycleManifest:
        self._assert_running("start_template")
        response = self._transport.request(
            "POST",
            f"/sandboxes/{self.id}/template/start",
            json_body=_template_start_payload(opts),
        )
        return TemplateLifecycleManifest(_read_result_data(response))

    def get_artifacts(self) -> SandboxArtifacts:
        response = self._transport.request("GET", f"/sandboxes/{self.id}/artifacts")
        return SandboxArtifacts(_read_result_data(response))

    def snapshot(self) -> str:
        self._assert_running("snapshot")
        response = self._transport.request("POST", f"/sandboxes/{self.id}/snapshot", json_body={})
        data = _read_result_data(response)
        return cast(str, data.get("snapshot_id") or data.get("id"))

    def get_logs(self, lines: int | None = None) -> dict[str, Any] | str:
        response = self._transport.request(
            "GET", f"/sandboxes/{self.id}/logs", params={"lines": lines}
        )
        data = _read_result_data(response)
        return data if data else cast(dict[str, Any] | str, response)

    def stream_logs(self) -> Iterator[SandboxEvent]:
        request = self._transport._client.build_request(
            "GET",
            f"/sandboxes/{self.id}/logs/stream",
            headers={"Accept": "text/event-stream"},
        )
        stream = self._transport._client.send(request, stream=True)
        try:
            if not stream.is_success:
                body = stream.read()
                parsed: Any = body.decode("utf-8", errors="replace")
                with contextlib.suppress(json.JSONDecodeError):
                    parsed = json.loads(parsed)
                raise_for_status(stream.status_code, parsed, stream.headers.get("x-request-id"))
            yield from _iter_sse(stream.iter_lines())
        finally:
            stream.close()

    def metrics(self, window: str = "1h") -> dict[str, Any]:
        """Read sandbox operational metrics and current resource state."""
        response = self._transport.request(
            "GET", f"/sandboxes/{self.id}/metrics", params={"window": window}
        )
        return _read_result_data(response)

    def get_metrics(self, window: str = "1h") -> dict[str, Any]:
        """Compatibility alias for :meth:`metrics`."""
        return self.metrics(window)

    def create_snapshot(self, comment: str | None = None) -> dict[str, Any]:
        self._assert_running("snapshots.create")
        response = self._transport.request(
            "POST",
            f"/sandboxes/{self.id}/snapshots",
            json_body={} if comment is None else {"comment": comment},
        )
        return _read_result_data(response)

    def list_snapshots(self) -> list[dict[str, Any]]:
        response = self._transport.request("GET", f"/sandboxes/{self.id}/snapshots")
        if isinstance(response, list):
            return cast(list[dict[str, Any]], response)
        if isinstance(response, dict):
            for key in ("data", "snapshots", "items"):
                items = response.get(key)
                if isinstance(items, list):
                    return cast(list[dict[str, Any]], items)
        return []

    def restore_snapshot(self, snapshot_id: str) -> Sandbox:
        response = self._transport.request(
            "POST", f"/sandboxes/{self.id}/restore/{snapshot_id}", json_body={}
        )
        return Sandbox(self._transport, _normalize_sandbox_payload(response))

    def delete_snapshot(self, snapshot_id: str) -> None:
        self._transport.request("DELETE", f"/sandboxes/{self.id}/snapshots/{snapshot_id}")

    def update(
        self,
        *,
        name: str | None = None,
        slug: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        always_on: bool | None = None,
        timeout_sec: int | None = None,
        idle_timeout_sec: int | None = None,
        persistent: bool | None = None,
        snapshot_expiration_sec: int | None = None,
        snapshot_expiration_days: int | None = None,
        keep_last_snapshots: int | dict[str, Any] | None = None,
    ) -> Sandbox:
        """PATCH /api/v1/sandboxes/{id} — update mutable sandbox fields."""
        metadata_body = dict(metadata or {})
        if persistent is not None:
            metadata_body["miosa_persistent"] = persistent
        if snapshot_expiration_sec is not None:
            metadata_body["snapshot_expiration_sec"] = snapshot_expiration_sec
        elif snapshot_expiration_days is not None:
            metadata_body["snapshot_expiration_sec"] = snapshot_expiration_days * 86_400
        if keep_last_snapshots is not None:
            metadata_body["keep_last_snapshots"] = keep_last_snapshots

        body: dict[str, Any] = {}
        for key, value in (
            ("name", name),
            ("slug", slug),
            ("tags", tags),
            ("metadata", metadata_body or None),
            ("always_on", always_on),
            ("timeout_sec", timeout_sec),
            ("idle_timeout_sec", idle_timeout_sec),
        ):
            if value is not None:
                body[key] = value
        response = self._transport.request("PATCH", f"/sandboxes/{self.id}", json_body=body)
        self._replace(_normalize_sandbox_payload(response))
        return self

    def extend(self, timeout_sec: int | None = None) -> Sandbox:
        """Extend or replace the sandbox activity timeout."""
        response = self._transport.request(
            "POST",
            f"/sandboxes/{self.id}/extend",
            json_body={} if timeout_sec is None else {"timeout_sec": timeout_sec},
        )
        self._replace({**self.data, **_normalize_sandbox_payload(response)})
        return self

    def usage(self) -> SandboxUsage:
        response = self._transport.request("GET", f"/sandboxes/{self.id}/usage")
        return cast(SandboxUsage, _normalize_sandbox_payload(response))

    def preview_token(self, expires_in: int = 3600, scope: str = "read") -> dict[str, Any]:
        """POST /api/v1/sandboxes/{id}/preview-token → {token, url, expires_at, scope}"""
        body = {"expires_in": expires_in, "scope": scope}
        return _unwrap_preview_token(
            self._transport.request("POST", f"/sandboxes/{self.id}/preview-token", json_body=body)
        )

    def pause(self) -> Sandbox:
        response = self._transport.request("POST", f"/sandboxes/{self.id}/pause", json_body={})
        self._replace({**self.data, **_normalize_sandbox_payload(response)})
        return self

    def resume(self, *, idempotency_key: str | None = None) -> Sandbox:
        response = self._transport.request(
            "POST",
            f"/sandboxes/{self.id}/resume",
            json_body={},
            headers={"Idempotency-Key": idempotency_key} if idempotency_key else None,
        )
        self._replace({**self.data, **_normalize_sandbox_payload(response)})
        return self

    def deploy(
        self,
        *,
        name: str | None = None,
        deployment_id: str | None = None,
        path: str | None = None,
        source_path: str | None = None,
        output_path: str | None = None,
        source_snapshot_path: str | None = None,
        entrypoint: str | None = None,
        build_command: str | None = None,
        run_command: str | None = None,
        start_command: str | None = None,
        port: int | None = None,
        health_check_path: str | None = None,
        deployment_type: str | None = None,
        type: str | None = None,
        mode: str | None = None,
        database: dict[str, Any] | bool | None = None,
        resources: dict[str, Any] | None = None,
        domain: str | None = None,
        custom_domain: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        response = self._transport.request(
            "POST",
            f"/sandboxes/{self.id}/deploy",
            json_body={
                key: value
                for key, value in {
                    "name": name,
                    "deployment_id": deployment_id,
                    "output_path": output_path or path or source_path,
                    "source_snapshot_path": source_snapshot_path,
                    "entrypoint": entrypoint,
                    "build_command": build_command,
                    "run_command": run_command,
                    "start_command": start_command,
                    "port": port,
                    "health_check_path": health_check_path,
                    "deployment_type": deployment_type,
                    "type": type,
                    "mode": mode,
                    "database": database,
                    "resources": resources,
                    "domain": domain,
                    "custom_domain": custom_domain,
                }.items()
                if value is not None
            },
            headers={"Idempotency-Key": idempotency_key} if idempotency_key else None,
        )
        return _read_result_data(response)

    def deploy_docker(self, **kwargs: Any) -> dict[str, Any]:
        """Deploy this sandbox through the workspace App Engine runtime."""
        kwargs["deployment_type"] = "docker_deploy"
        return self.deploy(**kwargs)

    def deploy_snapshot(
        self,
        snapshot_id: str,
        *,
        fork_idempotency_key: str | None = None,
        cleanup: bool = True,
        **deploy_kwargs: Any,
    ) -> dict[str, Any]:
        """Deploy an immutable snapshot without modifying the source sandbox."""
        release = self.fork(
            snapshot_id=snapshot_id,
            name=f"release-{snapshot_id[:12]}",
            metadata={"release_source_sandbox_id": self.id, "snapshot_id": snapshot_id},
            idempotency_key=fork_idempotency_key,
        )
        def destroy_release() -> Exception | None:
            if not cleanup:
                return None
            try:
                release.destroy()
            except Exception as exc:
                return exc
            return None

        try:
            result = release.deploy(**deploy_kwargs)
        except BaseException as exc:
            cleanup_error = destroy_release()
            if not cleanup or cleanup_error is not None:
                _report_surviving_release(exc, release.id, cleanup_error)
            raise
        cleanup_error = destroy_release()
        result["source_snapshot_id"] = snapshot_id
        result["release_sandbox_id"] = release.id
        if cleanup_error is not None:
            result["release_cleanup_error"] = str(cleanup_error)
        return result

    def fork(
        self,
        *,
        snapshot_id: str | None = None,
        name: str | None = None,
        external_user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        timeout_sec: int | None = None,
        template_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> Sandbox:
        """Fork (clone) this sandbox into a new sandbox.

        The fork is a copy-on-write snapshot of the current sandbox filesystem
        and process state. The original sandbox continues running unchanged.

        Args:
            snapshot_id: Optional snapshot to fork from instead of live state.
            name: Optional name for the forked sandbox.
            external_user_id: Optional white-label user attribution.
            metadata: Optional metadata dict for the forked sandbox.

        Returns:
            A new :class:`Sandbox` handle for the forked instance.

        Example::

            fork = sb.fork(name="my-fork")
            fork.exec("echo 'running in fork'")
            fork.destroy()
        """
        self._assert_running("fork")
        body: dict[str, Any] = {}
        if snapshot_id is not None:
            body["snapshot_id"] = snapshot_id
        if name is not None:
            body["name"] = name
        if external_user_id is not None:
            body["external_user_id"] = external_user_id
        if metadata is not None:
            body["metadata"] = metadata
        if timeout_sec is not None:
            body["timeout_sec"] = timeout_sec
        if template_id is not None:
            body["template_id"] = template_id
        response = self._transport.request(
            "POST",
            f"/sandboxes/{self.id}/fork",
            json_body=body,
            headers={"Idempotency-Key": idempotency_key} if idempotency_key else None,
        )
        return Sandbox(self._transport, _normalize_sandbox_payload(response))

    def destroy(self) -> None:
        if self.state == "destroyed":
            return
        response = self._transport.request("DELETE", f"/sandboxes/{self.id}")
        if isinstance(response, dict):
            data = _normalize_sandbox_payload(response)
            if data:
                self._replace({**self.data, **data, "state": data.get("state", "destroyed")})
                return
        self.state = "destroyed"
        self.destroyed_at = datetime.now()

    delete = destroy

    def _assert_running(self, operation: str) -> None:
        if self.state == "destroyed":
            raise MiosaError(f"Sandbox {self.id} has been destroyed")
        if self.state == "paused" and self.persistent:
            return
        if self.state != "running":
            raise MiosaError(
                f"Cannot {operation} on sandbox {self.id}: state is {self.state!r}, "
                "expected 'running' or paused persistent"
            )


class Sandboxes:
    """Synchronous native sandbox resource."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def create_agent_workspace(
        self,
        name: str,
        *,
        template_id: str | None = None,
        timeout_sec: int = AGENT_WORKSPACE_TIMEOUT_SEC,
        idle_timeout_sec: int = AGENT_WORKSPACE_IDLE_TIMEOUT_SEC,
        snapshot_expiration_sec: int = AGENT_WORKSPACE_SNAPSHOT_EXPIRATION_SEC,
        keep_last_snapshots: int | dict[str, Any] = AGENT_WORKSPACE_KEEP_LAST_SNAPSHOTS,
        wait_until_ready: bool = True,
        wait_timeout: float = 60.0,
        **kwargs: Any,
    ) -> Sandbox:
        """Create or resume a persistent sandbox for an AI agent workspace.

        Agents should create/edit files under ``/workspace``, run package
        installs/tests/builds inside this sandbox, expose previews from this
        sandbox, and publish from this sandbox. This helper avoids the old
        "upload a local repo, destroy on completion" flow for builder products.
        """
        metadata = dict(kwargs.pop("metadata", {}) or {})
        metadata.setdefault("miosa_workspace_kind", "agent_workspace")
        return self.get_or_create(
            name,
            template_id=template_id,
            persistent=True,
            timeout_sec=timeout_sec,
            idle_timeout_sec=idle_timeout_sec,
            snapshot_expiration_sec=snapshot_expiration_sec,
            keep_last_snapshots=keep_last_snapshots,
            wait_until_ready=wait_until_ready,
            wait_timeout=wait_timeout,
            metadata=metadata,
            **kwargs,
        )

    def create(
        self,
        template_id: str | None = None,
        *,
        image: str | None = None,
        size: SandboxSize | None = None,
        cpu_count: int | None = None,
        memory_mb: int | None = None,
        disk_mb: int | None = None,
        disk_size_mb: int | None = None,
        timeout_sec: int | None = None,
        env: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
        services: list[dict[str, Any]] | None = None,
        readiness_probe: dict[str, Any] | None = None,
        database: dict[str, Any] | bool | None = None,
        github_repo_url: str | None = None,
        github_branch: str | None = None,
        github_clone_path: str | None = None,
        name: str | None = None,
        region: str | None = None,
        idle_timeout_sec: int | None = None,
        persistent: bool | None = None,
        snapshot_expiration_sec: int | None = None,
        snapshot_expiration_days: int | None = None,
        keep_last_snapshots: int | dict[str, Any] | None = None,
        always_on: bool | None = None,
        entrypoint: str | None = None,
        tags: list[str] | None = None,
        idempotency_key: str | None = None,
        workspace_id: str | None = None,
        workspace_slug: str | None = None,
        workspace_name: str | None = None,
        project_id: str | None = None,
        project_slug: str | None = None,
        project_name: str | None = None,
        external_workspace_id: str | None = None,
        external_user_id: str | None = None,
        external_project_id: str | None = None,
        slug: str | None = None,
        agent_runtime_profile_id: str | None = None,
        agent_profile_id: str | None = None,
        skip_agent_runtime_profile: bool | None = None,
        allow_provision: bool | None = None,
        opts: CreateSandboxOptions | None = None,
    ) -> Sandbox:
        merged = _merge_create_options(
            template_id,
            image,
            size,
            cpu_count,
            memory_mb,
            disk_mb,
            disk_size_mb,
            timeout_sec,
            env,
            metadata,
            services,
            readiness_probe,
            database,
            github_repo_url,
            github_branch,
            github_clone_path,
            name,
            region,
            idle_timeout_sec,
            persistent,
            snapshot_expiration_sec,
            snapshot_expiration_days,
            keep_last_snapshots,
            always_on,
            entrypoint,
            tags,
            idempotency_key,
            opts,
            workspace_id=workspace_id,
            workspace_slug=workspace_slug,
            workspace_name=workspace_name,
            project_id=project_id,
            project_slug=project_slug,
            project_name=project_name,
            external_workspace_id=external_workspace_id,
            external_user_id=external_user_id,
            external_project_id=external_project_id,
            slug=slug,
            agent_runtime_profile_id=agent_runtime_profile_id,
            agent_profile_id=agent_profile_id,
            skip_agent_runtime_profile=skip_agent_runtime_profile,
            allow_provision=allow_provision,
        )
        headers = (
            {"Idempotency-Key": merged["idempotency_key"]}
            if "idempotency_key" in merged
            else None
        )
        data = self._transport.request(
            "POST", "/sandboxes", json_body=_build_create_body(merged), headers=headers
        )
        return Sandbox(self._transport, _normalize_sandbox_payload(data))

    def list(
        self,
        *,
        state: str | None = None,
        tags: list[str] | None = None,
        external_workspace_id: str | None = None,
        external_user_id: str | None = None,
        external_project_id: str | None = None,
    ) -> list[Sandbox]:
        params: dict[str, Any] = {"state": state}
        if tags:
            params["tags"] = ",".join(tags)
        if external_workspace_id is not None:
            params["external_workspace_id"] = external_workspace_id
        if external_user_id is not None:
            params["external_user_id"] = external_user_id
        if external_project_id is not None:
            params["external_project_id"] = external_project_id
        data = self._transport.request("GET", "/sandboxes", params=params)
        return [Sandbox(self._transport, item) for item in _normalize_list_payload(data)]

    def get(self, sandbox_id: str) -> Sandbox:
        data = self._transport.request("GET", f"/sandboxes/{sandbox_id}")
        return Sandbox(self._transport, _normalize_sandbox_payload(data))

    def connect(self, sandbox_id: str) -> Sandbox:
        return self.get(sandbox_id)

    def get_by_name(self, name: str) -> Sandbox:
        data = self._transport.request("GET", f"/sandboxes/by-name/{quote(name, safe='')}")
        return Sandbox(self._transport, _normalize_sandbox_payload(data))

    def get_or_create(
        self,
        name: str,
        *,
        resume: bool = True,
        wait_until_ready: bool = False,
        wait_timeout: float = 60.0,
        **kwargs: Any,
    ) -> Sandbox:
        """Return a sandbox by stable name, or create it if missing.

        Existing paused sandboxes are resumed by default. Destroyed sandboxes
        are permanent and are not silently reused.
        """
        try:
            sandbox = self.get_by_name(name)
        except NotFoundError:
            sandbox = self.create(name=name, **kwargs)

        if sandbox.state == "paused" and resume:
            sandbox.resume()

        if wait_until_ready:
            sandbox.wait_until_ready(wait_timeout)

        return sandbox

    def delete(self, sandbox_id: str) -> None:
        self._transport.request("DELETE", f"/sandboxes/{sandbox_id}")

    def list_templates(self, *, include_aliases: bool = False) -> dict[str, Any]:
        params = {"include_aliases": include_aliases} if include_aliases else None
        return cast(
            dict[str, Any],
            self._transport.request("GET", "/sandbox-templates", params=params),
        )

    def get_template(self, template_id: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._transport.request("GET", f"/sandbox-templates/{template_id}"),
        )

    def get_build_spec_schema(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._transport.request("GET", "/sandbox-templates/build-spec"))

    def validate_build_spec(self, build_spec: dict[str, Any]) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._transport.request(
                "POST",
                "/sandbox-templates/validate",
                json_body={"build_spec": build_spec},
            ),
        )

    def create_template(
        self,
        *,
        name: str,
        build_spec: dict[str, Any],
        slug: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name, "build_spec": build_spec}
        if slug is not None:
            body["slug"] = slug
        if description is not None:
            body["description"] = description
        if metadata is not None:
            body["metadata"] = metadata
        return cast(
            dict[str, Any],
            self._transport.request("POST", "/sandbox-templates", json_body=body),
        )

    def create_template_build(
        self,
        template_id: str,
        *,
        build_spec: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if build_spec is not None:
            body["build_spec"] = build_spec
        if metadata is not None:
            body["metadata"] = metadata
        return cast(
            dict[str, Any],
            self._transport.request(
                "POST",
                f"/sandbox-templates/{template_id}/builds",
                json_body=body,
            ),
        )

    def list_template_builds(self, template_id: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._transport.request("GET", f"/sandbox-templates/{template_id}/builds"),
        )

    def get_template_build(self, build_id: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._transport.request("GET", f"/sandbox-template-builds/{build_id}"),
        )


class AsyncSandbox:
    """Bound async handle for one native MIOSA sandbox."""

    def __init__(self, transport: AsyncTransport, data: dict[str, Any]) -> None:
        self._transport = transport
        self.exec = AsyncSandboxExecRunner(self)
        self.commands = AsyncSandboxCommands(self)
        self.files = AsyncSandboxFiles(self)
        self.git = AsyncSandboxGit(self)
        self.preview = AsyncSandboxPreview(self)
        self.previews = self.preview
        self.artifacts = AsyncSandboxArtifactsResource(self)
        self.logs = AsyncSandboxLogs(self)
        self.snapshots = AsyncSandboxSnapshots(self)
        self.events = AsyncSandboxEvents(self)
        self.env = AsyncSandboxEnv(self)
        self.terminal = AsyncSandboxTerminal(self)
        self.tags = AsyncSandboxTags(self)
        self.processes = AsyncSandboxProcesses(self)
        self.share = AsyncSandboxShare(self)
        # Egress (security) namespaces — pre-scoped to this sandbox id
        sandbox_id = str(data["id"])
        self.connectors = AsyncSandboxConnectors(transport, sandbox_id)
        self.secrets = AsyncSandboxSecrets(transport, sandbox_id)
        self.network = AsyncSandboxNetwork(transport, sandbox_id)
        self.audit = AsyncSandboxAudit(transport, sandbox_id)
        self._replace(data)

    def _replace(self, data: dict[str, Any]) -> None:
        self.data = data
        self.id = str(data["id"])
        self.state = cast(SandboxState, data.get("state", "provisioning"))
        self.ready = bool(data.get("ready", self.state == "running"))
        self.template_id = str(data.get("template_id") or data.get("image_id") or "")
        self.tenant_id = cast(str | None, data.get("tenant_id"))
        self.owner_id = cast(str | None, data.get("owner_id"))
        self.workspace_id = cast(str | None, data.get("workspace_id"))
        self.workspace_slug = cast(str | None, data.get("workspace_slug"))
        self.workspace_name = cast(str | None, data.get("workspace_name"))
        self.project_id = cast(str | None, data.get("project_id"))
        self.project_slug = cast(str | None, data.get("project_slug"))
        self.project_name = cast(str | None, data.get("project_name"))
        self.external_workspace_id = cast(str | None, data.get("external_workspace_id"))
        self.external_user_id = cast(str | None, data.get("external_user_id"))
        self.external_project_id = cast(str | None, data.get("external_project_id"))
        self.size = cast(SandboxSize | None, data.get("size"))
        self.resource_contract = cast(dict[str, Any] | None, data.get("resource_contract"))
        self.image_id = cast(str | None, data.get("image_id"))
        self.cpu_count = cast(int | None, data.get("cpu_count"))
        self.memory_mb = cast(int | None, data.get("memory_mb"))
        self.disk_size_mb = cast(int | None, data.get("disk_size_mb") or data.get("disk_mb"))
        self.timeout_sec = cast(int | None, data.get("timeout_sec"))
        self.timeout_remaining_ms = cast(int | None, data.get("timeout_remaining_ms"))
        self.idle_timeout_sec = cast(int | None, data.get("idle_timeout_sec"))
        self.always_on = bool(data.get("always_on", False))
        self.persistent = bool(data.get("persistent", False))
        self.slug = cast(str | None, data.get("slug"))
        self.name = cast(str | None, data.get("name"))
        self.metadata = cast(dict[str, Any], data.get("metadata") or {})
        self.preview_url = cast(str | None, data.get("preview_url"))
        self.url_info = cast(dict[str, Any] | None, data.get("url_info"))
        self.url_class = cast(str | None, data.get("url_class"))
        self.stable_for_embedding = cast(bool | None, data.get("stable_for_embedding"))
        self.recommended_next_action = cast(str | None, data.get("recommended_next_action"))
        self.preview_domain = cast(str | None, data.get("preview_domain"))
        self.boot_path = cast(str | None, data.get("boot_path"))
        self.boot_ms = cast(int | None, data.get("boot_ms"))
        self.created_at = _parse_iso(data.get("created_at") or data.get("inserted_at"))
        self.started_at = _parse_iso(data.get("started_at"))
        self.ready_at = _parse_iso(data.get("ready_at"))
        self.destroyed_at = _parse_iso(data.get("destroyed_at"))
        self.total_runtime_sec = cast(int | None, data.get("total_runtime_sec"))

    async def __aenter__(self) -> AsyncSandbox:
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        if self.state != "destroyed":
            with contextlib.suppress(Exception):
                await self.destroy()

    def __repr__(self) -> str:
        return (
            f"AsyncSandbox(id={self.id!r}, state={self.state!r}, "
            f"template_id={self.template_id!r})"
        )

    async def refresh(self) -> AsyncSandbox:
        data = await self._transport.request("GET", f"/sandboxes/{self.id}")
        self._replace(_normalize_sandbox_payload(data))
        return self

    async def run_agent(
        self,
        instruction: str,
        *,
        runner: str = "claude-code",
        provider: str | None = None,
        model: str | None = None,
        cwd: str = "/workspace",
        timeout: int | None = None,
        wait: bool = True,
        env: dict[str, str] | None = None,
        output_format: str | None = None,
        resume_session_id: str | None = None,
        json: bool | None = None,
        output_schema: str | None = None,
        image: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Run an AI coding agent inside this Sandbox."""
        body = {
            "instruction": instruction,
            "target_kind": "sandbox",
            "target_id": self.id,
            "runtime_id": self.id,
            "sandbox_id": self.id,
            "runner": runner,
            "provider": provider,
            "model": model,
            "cwd": cwd,
            "timeout": timeout,
            "wait": wait,
            "env": env,
            "output_format": output_format,
            "resume_session_id": resume_session_id,
            "json": json,
            "output_schema": output_schema,
            "image": image,
            **kwargs,
        }
        body = {key: value for key, value in body.items() if value is not None}
        return cast(
            dict[str, Any],
            _read_result_data(
                await self._transport.request("POST", "/runs", json_body=body)
            ),
        )

    async def prompt(
        self,
        prompt: str,
        *,
        provider: str | None = "claude",
        model: str | None = None,
        cwd: str = "/workspace",
        timeout: int | None = None,
        wait: bool = True,
        env: dict[str, str] | None = None,
        output_format: str | None = None,
        resume_session_id: str | None = None,
        json: bool | None = None,
        output_schema: str | None = None,
        image: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Dispatch a prompt into this Sandbox through the Agent Runs API."""
        body = {
            "prompt": prompt,
            "target_kind": "sandbox",
            "target_id": self.id,
            "sandbox_id": self.id,
            "provider": provider,
            "model": model,
            "cwd": cwd,
            "timeout": timeout,
            "wait": wait,
            "env": env,
            "output_format": output_format,
            "resume_session_id": resume_session_id,
            "json": json,
            "output_schema": output_schema,
            "image": image,
            **kwargs,
        }
        body = {key: value for key, value in body.items() if value is not None}
        return cast(
            dict[str, Any],
            _read_result_data(
                await self._transport.request("POST", "/agent-runs", json_body=body)
            ),
        )

    async def readiness(self) -> dict[str, Any]:
        """Return the sandbox readiness-probe state."""
        response = await self._transport.request("GET", f"/sandboxes/{self.id}/readiness")
        return _read_result_data(response) if response else {}

    async def wait_until_ready(self, timeout: float = 30.0, stream: bool = True) -> bool:
        """Async counterpart of :meth:`Sandbox.wait_until_ready`."""
        if stream:
            try:
                request = self._transport._client.build_request(
                    "GET",
                    f"/sandboxes/{self.id}/readiness/stream",
                    headers={"Accept": "text/event-stream"},
                    timeout=timeout + 5.0,
                )
                response = await self._transport._client.send(request, stream=True)
                try:
                    if response.status_code == 404:
                        await response.aread()
                        # fall through to polling fallback below
                    elif not response.is_success:
                        body = await response.aread()
                        parsed: Any = body.decode("utf-8", errors="replace")
                        with contextlib.suppress(json.JSONDecodeError):
                            parsed = json.loads(parsed)
                        raise_for_status(
                            response.status_code,
                            parsed,
                            response.headers.get("x-request-id"),
                        )
                    else:
                        async for raw_line in response.aiter_lines():
                            line = (
                                raw_line
                                if isinstance(raw_line, str)
                                else raw_line.decode("utf-8", errors="replace")
                            )
                            if line.startswith("event: ready") or line.startswith("event:ready"):
                                return True
                            if line.startswith("event: timeout") or line.startswith(
                                "event:timeout"
                            ):
                                return False
                        # stream closed without a terminal event — fall through
                finally:
                    await response.aclose()
            except (httpx.HTTPError, OSError):
                pass

        # Polling fallback (no exponential backoff — fixed 10 ms tick).
        import asyncio  # local import — async polling fallback only
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                data = await self.readiness()
            except MiosaError:
                data = {}
            if data.get("ready") or data.get("status") == "ready":
                return True
            await asyncio.sleep(0.01)
        return False

    async def _run_exec(self, command: str, opts: ExecOptions | None = None) -> ExecResult:
        self._assert_running("exec")
        start_ms = time.monotonic()
        response = await self._transport.request(
            "POST", f"/sandboxes/{self.id}/exec", json_body=_exec_payload(command, opts)
        )
        data = _read_result_data(response)
        return ExecResult(
            stdout=str(data.get("stdout", "")),
            stderr=str(data.get("stderr", "")),
            exit_code=int(data.get("exit_code", data.get("exitCode", 0))),
            duration_ms=int(data.get("duration_ms") or (time.monotonic() - start_ms) * 1000),
        )

    async def exec_stream(
        self, command: str, opts: ExecOptions | None = None
    ) -> AsyncIterator[SandboxEvent]:
        self._assert_running("exec_stream")
        request = self._transport._client.build_request(
            "POST",
            f"/sandboxes/{self.id}/exec/stream",
            json=_exec_payload(command, opts),
            headers={"Accept": "text/event-stream"},
        )
        stream = await self._transport._client.send(request, stream=True)
        try:
            if not stream.is_success:
                body = await stream.aread()
                parsed: Any = body.decode("utf-8", errors="replace")
                with contextlib.suppress(json.JSONDecodeError):
                    parsed = json.loads(parsed)
                raise_for_status(stream.status_code, parsed, stream.headers.get("x-request-id"))
            async for event in _aiter_sse(stream.aiter_lines()):
                yield event
        finally:
            await stream.aclose()

    async def run(self, command: str, opts: ExecOptions | None = None) -> ExecResult:
        return await self.exec.run(command, opts)

    async def write_file(self, path: str, content: bytes | str | Path) -> None:
        await self.upload(path, content)

    async def upload(self, path: str, content: bytes | str | Path) -> None:
        self._assert_running("upload")
        await self._transport.request(
            "POST",
            f"/sandboxes/{self.id}/files",
            json_body={"path": path, "content": _to_base64(content)},
        )

    async def download(self, path: str) -> bytes:
        self._assert_running("download")
        response = await self._transport.request(
            "GET", f"/sandboxes/{self.id}/files/{path.lstrip('/')}", raw_response=True
        )
        body: bytes = response.content
        content_type = response.headers.get("content-type", "")
        raise_for_status(response.status_code, response.text, response.headers.get("x-request-id"))
        if "application/json" not in content_type:
            return body
        parsed = response.json()
        data = _read_result_data(parsed)
        content = data.get("content", "")
        if isinstance(content, str):
            with contextlib.suppress(ValueError, TypeError):
                return base64.b64decode(content)
            return content.encode("utf-8")
        return b""

    async def create_export(
        self,
        paths: str | list[str],
        *,
        label: str | None = None,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """Create a portable export descriptor for sandbox-generated files."""
        body: dict[str, Any] = {"path": paths} if isinstance(paths, str) else {"paths": paths}
        if label is not None:
            body["label"] = label
        if filename is not None:
            body["filename"] = filename
        response = await self._transport.request(
            "POST", f"/sandboxes/{self.id}/exports", json_body=body
        )
        return _read_result_data(response)

    async def download_export(
        self, paths: str | list[str], *, filename: str | None = None
    ) -> bytes:
        """Download one exported file or a tar.gz archive for multiple paths."""
        query_items: list[tuple[str, str]] = []
        if isinstance(paths, str):
            query_items.append(("path", paths))
        else:
            query_items.extend(("paths[]", path) for path in paths)
        if filename is not None:
            query_items.append(("filename", filename))
        query = urlencode(query_items)
        response = await self._transport.request(
            "GET", f"/sandboxes/{self.id}/exports/download?{query}", raw_response=True
        )
        raise_for_status(response.status_code, response.text, response.headers.get("x-request-id"))
        return cast(bytes, response.content)

    async def read_file(self, path: str, *, text: bool = True) -> str | bytes:
        data = await self.download(path)
        return data.decode("utf-8") if text else data

    async def list_files(
        self, path: str = "/workspace", *, depth: int | None = None
    ) -> dict[str, Any]:
        self._assert_running("files.list")
        params: dict[str, Any] = {"path": path}
        if depth is not None:
            params["depth"] = depth
        response = await self._transport.request(
            "GET", f"/sandboxes/{self.id}/files", params=params
        )
        return _read_result_data(response)

    async def stat_file(self, path: str) -> dict[str, Any]:
        self._assert_running("files.stat")
        response = await self._transport.request(
            "POST", f"/sandboxes/{self.id}/files/stat", json_body={"path": path}
        )
        return _read_result_data(response)

    async def expose(self, port: int | None = None) -> str:
        return (await self.expose_info(port)).url

    async def get_url(self, port: int | None = None, path: str = "/") -> str:
        parsed = urlparse((await self.expose_info(port)).url)
        normalized_path = path if path.startswith("/") else f"/{path}"
        return urlunparse(parsed._replace(path=normalized_path))

    async def get_host(self, port: int | None = None) -> str:
        return urlparse((await self.expose_info(port)).url).netloc

    async def expose_info(self, port: int | None = None) -> PreviewUrlInfo:
        self._assert_running("expose")
        response = await self._transport.request(
            "POST",
            f"/sandboxes/{self.id}/expose",
            json_body={} if port is None else {"port": port},
        )
        data = _read_result_data(response)
        url = cast(str | None, data.get("url") or data.get("preview_url") or response.get("url"))
        merged = dict(data)
        merged["url"] = cast(str, _normalize_preview_url(url))
        return PreviewUrlInfo(_normalize_preview_info(merged))

    async def start_template(
        self, opts: StartTemplateOptions | None = None
    ) -> TemplateLifecycleManifest:
        self._assert_running("start_template")
        response = await self._transport.request(
            "POST",
            f"/sandboxes/{self.id}/template/start",
            json_body=_template_start_payload(opts),
        )
        return TemplateLifecycleManifest(_read_result_data(response))

    async def get_artifacts(self) -> SandboxArtifacts:
        response = await self._transport.request("GET", f"/sandboxes/{self.id}/artifacts")
        return SandboxArtifacts(_read_result_data(response))

    async def snapshot(self) -> str:
        self._assert_running("snapshot")
        response = await self._transport.request(
            "POST", f"/sandboxes/{self.id}/snapshot", json_body={}
        )
        data = _read_result_data(response)
        return cast(str, data.get("snapshot_id") or data.get("id"))

    async def get_logs(self, lines: int | None = None) -> dict[str, Any] | str:
        response = await self._transport.request(
            "GET", f"/sandboxes/{self.id}/logs", params={"lines": lines}
        )
        data = _read_result_data(response)
        return data if data else cast(dict[str, Any] | str, response)

    async def stream_logs(self) -> AsyncIterator[SandboxEvent]:
        request = self._transport._client.build_request(
            "GET",
            f"/sandboxes/{self.id}/logs/stream",
            headers={"Accept": "text/event-stream"},
        )
        stream = await self._transport._client.send(request, stream=True)
        try:
            if not stream.is_success:
                body = await stream.aread()
                parsed: Any = body.decode("utf-8", errors="replace")
                with contextlib.suppress(json.JSONDecodeError):
                    parsed = json.loads(parsed)
                raise_for_status(stream.status_code, parsed, stream.headers.get("x-request-id"))
            async for event in _aiter_sse(stream.aiter_lines()):
                yield event
        finally:
            await stream.aclose()

    async def metrics(self, window: str = "1h") -> dict[str, Any]:
        """Read sandbox operational metrics and current resource state."""
        response = await self._transport.request(
            "GET", f"/sandboxes/{self.id}/metrics", params={"window": window}
        )
        return _read_result_data(response)

    async def get_metrics(self, window: str = "1h") -> dict[str, Any]:
        """Compatibility alias for :meth:`metrics`."""
        return await self.metrics(window)

    async def create_snapshot(self, comment: str | None = None) -> dict[str, Any]:
        self._assert_running("snapshots.create")
        response = await self._transport.request(
            "POST",
            f"/sandboxes/{self.id}/snapshots",
            json_body={} if comment is None else {"comment": comment},
        )
        return _read_result_data(response)

    async def list_snapshots(self) -> list[dict[str, Any]]:
        response = await self._transport.request("GET", f"/sandboxes/{self.id}/snapshots")
        if isinstance(response, list):
            return cast(list[dict[str, Any]], response)
        if isinstance(response, dict):
            for key in ("data", "snapshots", "items"):
                items = response.get(key)
                if isinstance(items, list):
                    return cast(list[dict[str, Any]], items)
        return []

    async def restore_snapshot(self, snapshot_id: str) -> AsyncSandbox:
        response = await self._transport.request(
            "POST", f"/sandboxes/{self.id}/restore/{snapshot_id}", json_body={}
        )
        return AsyncSandbox(self._transport, _normalize_sandbox_payload(response))

    async def delete_snapshot(self, snapshot_id: str) -> None:
        await self._transport.request("DELETE", f"/sandboxes/{self.id}/snapshots/{snapshot_id}")

    async def update(
        self,
        *,
        name: str | None = None,
        slug: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        always_on: bool | None = None,
        timeout_sec: int | None = None,
        idle_timeout_sec: int | None = None,
        persistent: bool | None = None,
        snapshot_expiration_sec: int | None = None,
        snapshot_expiration_days: int | None = None,
        keep_last_snapshots: int | dict[str, Any] | None = None,
    ) -> AsyncSandbox:
        """PATCH /api/v1/sandboxes/{id} — update mutable sandbox fields."""
        metadata_body = dict(metadata or {})
        if persistent is not None:
            metadata_body["miosa_persistent"] = persistent
        if snapshot_expiration_sec is not None:
            metadata_body["snapshot_expiration_sec"] = snapshot_expiration_sec
        elif snapshot_expiration_days is not None:
            metadata_body["snapshot_expiration_sec"] = snapshot_expiration_days * 86_400
        if keep_last_snapshots is not None:
            metadata_body["keep_last_snapshots"] = keep_last_snapshots

        body: dict[str, Any] = {}
        for key, value in (
            ("name", name),
            ("slug", slug),
            ("tags", tags),
            ("metadata", metadata_body or None),
            ("always_on", always_on),
            ("timeout_sec", timeout_sec),
            ("idle_timeout_sec", idle_timeout_sec),
        ):
            if value is not None:
                body[key] = value
        response = await self._transport.request("PATCH", f"/sandboxes/{self.id}", json_body=body)
        self._replace(_normalize_sandbox_payload(response))
        return self

    async def extend(self, timeout_sec: int | None = None) -> AsyncSandbox:
        """Extend or replace the sandbox activity timeout."""
        response = await self._transport.request(
            "POST",
            f"/sandboxes/{self.id}/extend",
            json_body={} if timeout_sec is None else {"timeout_sec": timeout_sec},
        )
        self._replace({**self.data, **_normalize_sandbox_payload(response)})
        return self

    async def usage(self) -> SandboxUsage:
        response = await self._transport.request("GET", f"/sandboxes/{self.id}/usage")
        return cast(SandboxUsage, _normalize_sandbox_payload(response))

    async def preview_token(self, expires_in: int = 3600, scope: str = "read") -> dict[str, Any]:
        """POST /api/v1/sandboxes/{id}/preview-token → {token, url, expires_at, scope}"""
        body = {"expires_in": expires_in, "scope": scope}
        return _unwrap_preview_token(
            await self._transport.request(
                "POST", f"/sandboxes/{self.id}/preview-token", json_body=body
            )
        )

    async def pause(self) -> AsyncSandbox:
        response = await self._transport.request(
            "POST", f"/sandboxes/{self.id}/pause", json_body={}
        )
        self._replace({**self.data, **_normalize_sandbox_payload(response)})
        return self

    async def resume(self, *, idempotency_key: str | None = None) -> AsyncSandbox:
        response = await self._transport.request(
            "POST",
            f"/sandboxes/{self.id}/resume",
            json_body={},
            headers={"Idempotency-Key": idempotency_key} if idempotency_key else None,
        )
        self._replace({**self.data, **_normalize_sandbox_payload(response)})
        return self

    async def deploy(
        self,
        *,
        name: str | None = None,
        deployment_id: str | None = None,
        path: str | None = None,
        source_path: str | None = None,
        output_path: str | None = None,
        source_snapshot_path: str | None = None,
        entrypoint: str | None = None,
        build_command: str | None = None,
        run_command: str | None = None,
        start_command: str | None = None,
        port: int | None = None,
        health_check_path: str | None = None,
        deployment_type: str | None = None,
        type: str | None = None,
        mode: str | None = None,
        database: dict[str, Any] | bool | None = None,
        resources: dict[str, Any] | None = None,
        domain: str | None = None,
        custom_domain: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        response = await self._transport.request(
            "POST",
            f"/sandboxes/{self.id}/deploy",
            json_body={
                key: value
                for key, value in {
                    "name": name,
                    "deployment_id": deployment_id,
                    "output_path": output_path or path or source_path,
                    "source_snapshot_path": source_snapshot_path,
                    "entrypoint": entrypoint,
                    "build_command": build_command,
                    "run_command": run_command,
                    "start_command": start_command,
                    "port": port,
                    "health_check_path": health_check_path,
                    "deployment_type": deployment_type,
                    "type": type,
                    "mode": mode,
                    "database": database,
                    "resources": resources,
                    "domain": domain,
                    "custom_domain": custom_domain,
                }.items()
                if value is not None
            },
            headers={"Idempotency-Key": idempotency_key} if idempotency_key else None,
        )
        return _read_result_data(response)

    async def deploy_docker(self, **kwargs: Any) -> dict[str, Any]:
        """Deploy this sandbox through the workspace App Engine runtime."""
        kwargs["deployment_type"] = "docker_deploy"
        return await self.deploy(**kwargs)

    async def deploy_snapshot(
        self,
        snapshot_id: str,
        *,
        fork_idempotency_key: str | None = None,
        cleanup: bool = True,
        **deploy_kwargs: Any,
    ) -> dict[str, Any]:
        """Deploy an immutable snapshot without modifying the source sandbox."""
        release = await self.fork(
            snapshot_id=snapshot_id,
            name=f"release-{snapshot_id[:12]}",
            metadata={"release_source_sandbox_id": self.id, "snapshot_id": snapshot_id},
            idempotency_key=fork_idempotency_key,
        )
        async def destroy_release() -> Exception | None:
            if not cleanup:
                return None
            try:
                await release.destroy()
            except Exception as exc:
                return exc
            return None

        try:
            result = await release.deploy(**deploy_kwargs)
        except BaseException as exc:
            cleanup_error = await destroy_release()
            if not cleanup or cleanup_error is not None:
                _report_surviving_release(exc, release.id, cleanup_error)
            raise
        cleanup_error = await destroy_release()
        result["source_snapshot_id"] = snapshot_id
        result["release_sandbox_id"] = release.id
        if cleanup_error is not None:
            result["release_cleanup_error"] = str(cleanup_error)
        return result

    async def fork(
        self,
        *,
        snapshot_id: str | None = None,
        name: str | None = None,
        external_user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        timeout_sec: int | None = None,
        template_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> AsyncSandbox:
        """Fork (clone) this sandbox into a new sandbox.

        Args:
            snapshot_id: Optional snapshot to fork from instead of live state.
            name: Optional name for the forked sandbox.
            external_user_id: Optional white-label user attribution.
            metadata: Optional metadata dict for the forked sandbox.

        Example::

            fork = await sb.fork(name="my-fork")
            await fork.exec("echo 'running in fork'")
            await fork.destroy()
        """
        self._assert_running("fork")
        body: dict[str, Any] = {}
        if snapshot_id is not None:
            body["snapshot_id"] = snapshot_id
        if name is not None:
            body["name"] = name
        if external_user_id is not None:
            body["external_user_id"] = external_user_id
        if metadata is not None:
            body["metadata"] = metadata
        if timeout_sec is not None:
            body["timeout_sec"] = timeout_sec
        if template_id is not None:
            body["template_id"] = template_id
        response = await self._transport.request(
            "POST",
            f"/sandboxes/{self.id}/fork",
            json_body=body,
            headers={"Idempotency-Key": idempotency_key} if idempotency_key else None,
        )
        return AsyncSandbox(self._transport, _normalize_sandbox_payload(response))

    async def destroy(self) -> None:
        if self.state == "destroyed":
            return
        response = await self._transport.request("DELETE", f"/sandboxes/{self.id}")
        if isinstance(response, dict):
            data = _normalize_sandbox_payload(response)
            if data:
                self._replace({**self.data, **data, "state": data.get("state", "destroyed")})
                return
        self.state = "destroyed"
        self.destroyed_at = datetime.now()

    delete = destroy

    def _assert_running(self, operation: str) -> None:
        if self.state == "destroyed":
            raise MiosaError(f"Sandbox {self.id} has been destroyed")
        if self.state == "paused" and self.persistent:
            return
        if self.state != "running":
            raise MiosaError(
                f"Cannot {operation} on sandbox {self.id}: state is {self.state!r}, "
                "expected 'running' or paused persistent"
            )


class AsyncSandboxes:
    """Asynchronous native sandbox resource."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def create_agent_workspace(
        self,
        name: str,
        *,
        template_id: str | None = None,
        timeout_sec: int = AGENT_WORKSPACE_TIMEOUT_SEC,
        idle_timeout_sec: int = AGENT_WORKSPACE_IDLE_TIMEOUT_SEC,
        snapshot_expiration_sec: int = AGENT_WORKSPACE_SNAPSHOT_EXPIRATION_SEC,
        keep_last_snapshots: int | dict[str, Any] = AGENT_WORKSPACE_KEEP_LAST_SNAPSHOTS,
        wait_until_ready: bool = True,
        wait_timeout: float = 60.0,
        **kwargs: Any,
    ) -> AsyncSandbox:
        """Create or resume a persistent sandbox for an AI agent workspace."""
        metadata = dict(kwargs.pop("metadata", {}) or {})
        metadata.setdefault("miosa_workspace_kind", "agent_workspace")
        return await self.get_or_create(
            name,
            template_id=template_id,
            persistent=True,
            timeout_sec=timeout_sec,
            idle_timeout_sec=idle_timeout_sec,
            snapshot_expiration_sec=snapshot_expiration_sec,
            keep_last_snapshots=keep_last_snapshots,
            wait_until_ready=wait_until_ready,
            wait_timeout=wait_timeout,
            metadata=metadata,
            **kwargs,
        )

    async def create(
        self,
        template_id: str | None = None,
        *,
        image: str | None = None,
        size: SandboxSize | None = None,
        cpu_count: int | None = None,
        memory_mb: int | None = None,
        disk_mb: int | None = None,
        disk_size_mb: int | None = None,
        timeout_sec: int | None = None,
        env: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
        services: list[dict[str, Any]] | None = None,
        readiness_probe: dict[str, Any] | None = None,
        database: dict[str, Any] | bool | None = None,
        github_repo_url: str | None = None,
        github_branch: str | None = None,
        github_clone_path: str | None = None,
        name: str | None = None,
        region: str | None = None,
        idle_timeout_sec: int | None = None,
        persistent: bool | None = None,
        snapshot_expiration_sec: int | None = None,
        snapshot_expiration_days: int | None = None,
        keep_last_snapshots: int | dict[str, Any] | None = None,
        always_on: bool | None = None,
        entrypoint: str | None = None,
        tags: list[str] | None = None,
        idempotency_key: str | None = None,
        workspace_id: str | None = None,
        workspace_slug: str | None = None,
        workspace_name: str | None = None,
        project_id: str | None = None,
        project_slug: str | None = None,
        project_name: str | None = None,
        external_workspace_id: str | None = None,
        external_user_id: str | None = None,
        external_project_id: str | None = None,
        slug: str | None = None,
        agent_runtime_profile_id: str | None = None,
        agent_profile_id: str | None = None,
        skip_agent_runtime_profile: bool | None = None,
        allow_provision: bool | None = None,
        opts: CreateSandboxOptions | None = None,
    ) -> AsyncSandbox:
        merged = _merge_create_options(
            template_id,
            image,
            size,
            cpu_count,
            memory_mb,
            disk_mb,
            disk_size_mb,
            timeout_sec,
            env,
            metadata,
            services,
            readiness_probe,
            database,
            github_repo_url,
            github_branch,
            github_clone_path,
            name,
            region,
            idle_timeout_sec,
            persistent,
            snapshot_expiration_sec,
            snapshot_expiration_days,
            keep_last_snapshots,
            always_on,
            entrypoint,
            tags,
            idempotency_key,
            opts,
            workspace_id=workspace_id,
            workspace_slug=workspace_slug,
            workspace_name=workspace_name,
            project_id=project_id,
            project_slug=project_slug,
            project_name=project_name,
            external_workspace_id=external_workspace_id,
            external_user_id=external_user_id,
            external_project_id=external_project_id,
            slug=slug,
            agent_runtime_profile_id=agent_runtime_profile_id,
            agent_profile_id=agent_profile_id,
            skip_agent_runtime_profile=skip_agent_runtime_profile,
            allow_provision=allow_provision,
        )
        headers = (
            {"Idempotency-Key": merged["idempotency_key"]}
            if "idempotency_key" in merged
            else None
        )
        data = await self._transport.request(
            "POST", "/sandboxes", json_body=_build_create_body(merged), headers=headers
        )
        return AsyncSandbox(self._transport, _normalize_sandbox_payload(data))

    async def list(
        self,
        *,
        state: str | None = None,
        tags: list[str] | None = None,
        external_workspace_id: str | None = None,
        external_user_id: str | None = None,
        external_project_id: str | None = None,
    ) -> list[AsyncSandbox]:
        params: dict[str, Any] = {"state": state}
        if tags:
            params["tags"] = ",".join(tags)
        if external_workspace_id is not None:
            params["external_workspace_id"] = external_workspace_id
        if external_user_id is not None:
            params["external_user_id"] = external_user_id
        if external_project_id is not None:
            params["external_project_id"] = external_project_id
        data = await self._transport.request("GET", "/sandboxes", params=params)
        return [AsyncSandbox(self._transport, item) for item in _normalize_list_payload(data)]

    async def get(self, sandbox_id: str) -> AsyncSandbox:
        data = await self._transport.request("GET", f"/sandboxes/{sandbox_id}")
        return AsyncSandbox(self._transport, _normalize_sandbox_payload(data))

    async def connect(self, sandbox_id: str) -> AsyncSandbox:
        return await self.get(sandbox_id)

    async def get_by_name(self, name: str) -> AsyncSandbox:
        data = await self._transport.request("GET", f"/sandboxes/by-name/{quote(name, safe='')}")
        return AsyncSandbox(self._transport, _normalize_sandbox_payload(data))

    async def get_or_create(
        self,
        name: str,
        *,
        resume: bool = True,
        wait_until_ready: bool = False,
        wait_timeout: float = 60.0,
        **kwargs: Any,
    ) -> AsyncSandbox:
        """Return a sandbox by stable name, or create it if missing."""
        try:
            sandbox = await self.get_by_name(name)
        except NotFoundError:
            sandbox = await self.create(name=name, **kwargs)

        if sandbox.state == "paused" and resume:
            await sandbox.resume()

        if wait_until_ready:
            await sandbox.wait_until_ready(wait_timeout)

        return sandbox

    async def delete(self, sandbox_id: str) -> None:
        await self._transport.request("DELETE", f"/sandboxes/{sandbox_id}")

    async def list_templates(self, *, include_aliases: bool = False) -> dict[str, Any]:
        params = {"include_aliases": include_aliases} if include_aliases else None
        return cast(
            dict[str, Any],
            await self._transport.request("GET", "/sandbox-templates", params=params),
        )

    async def get_template(self, template_id: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._transport.request("GET", f"/sandbox-templates/{template_id}"),
        )

    async def get_build_spec_schema(self) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._transport.request("GET", "/sandbox-templates/build-spec"),
        )

    async def validate_build_spec(self, build_spec: dict[str, Any]) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._transport.request(
                "POST",
                "/sandbox-templates/validate",
                json_body={"build_spec": build_spec},
            ),
        )

    async def create_template(
        self,
        *,
        name: str,
        build_spec: dict[str, Any],
        slug: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name, "build_spec": build_spec}
        if slug is not None:
            body["slug"] = slug
        if description is not None:
            body["description"] = description
        if metadata is not None:
            body["metadata"] = metadata
        return cast(
            dict[str, Any],
            await self._transport.request("POST", "/sandbox-templates", json_body=body),
        )

    async def create_template_build(
        self,
        template_id: str,
        *,
        build_spec: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if build_spec is not None:
            body["build_spec"] = build_spec
        if metadata is not None:
            body["metadata"] = metadata
        return cast(
            dict[str, Any],
            await self._transport.request(
                "POST",
                f"/sandbox-templates/{template_id}/builds",
                json_body=body,
            ),
        )

    async def list_template_builds(self, template_id: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._transport.request("GET", f"/sandbox-templates/{template_id}/builds"),
        )

    async def get_template_build(self, build_id: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._transport.request("GET", f"/sandbox-template-builds/{build_id}"),
        )


def _iter_sse(lines: Iterator[str]) -> Iterator[SandboxEvent]:
    event_type: str | None = None
    event_id: str | None = None
    data_lines: list[str] = []
    for line in lines:
        if not line:
            if data_lines:
                payload = "\n".join(data_lines)
                data: dict[str, Any]
                with contextlib.suppress(json.JSONDecodeError):
                    parsed = json.loads(payload)
                    data = parsed if isinstance(parsed, dict) else {"raw": parsed}
                    yield SandboxEvent(type=event_type or "message", data=data, id=event_id)
                    event_type = None
                    event_id = None
                    data_lines = []
                    continue
                yield SandboxEvent(type=event_type or "message", data={"raw": payload}, id=event_id)
            event_type = None
            event_id = None
            data_lines = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_type = line[len("event:") :].strip()
        elif line.startswith("id:"):
            event_id = line[len("id:") :].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:") :].strip())


async def _aiter_sse(lines: AsyncIterator[str]) -> AsyncIterator[SandboxEvent]:
    event_type: str | None = None
    event_id: str | None = None
    data_lines: list[str] = []
    async for line in lines:
        if not line:
            if data_lines:
                payload = "\n".join(data_lines)
                data: dict[str, Any]
                with contextlib.suppress(json.JSONDecodeError):
                    parsed = json.loads(payload)
                    data = parsed if isinstance(parsed, dict) else {"raw": parsed}
                    yield SandboxEvent(type=event_type or "message", data=data, id=event_id)
                    event_type = None
                    event_id = None
                    data_lines = []
                    continue
                yield SandboxEvent(type=event_type or "message", data={"raw": payload}, id=event_id)
            event_type = None
            event_id = None
            data_lines = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_type = line[len("event:") :].strip()
        elif line.startswith("id:"):
            event_id = line[len("id:") :].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:") :].strip())


__all__ = [
    "AsyncSandbox",
    "AsyncSandboxArtifactsResource",
    "AsyncSandboxCommands",
    "AsyncSandboxEnv",
    "AsyncSandboxEvents",
    "AsyncSandboxExecRunner",
    "AsyncSandboxFiles",
    "AsyncSandboxLogs",
    "AsyncSandboxPreview",
    "AsyncSandboxSnapshots",
    "AsyncSandboxTags",
    "AsyncSandboxTerminal",
    "AsyncSandboxes",
    "CreateSandboxOptions",
    "DEFAULT_TEMPLATE",
    "ExecOptions",
    "ExecResult",
    "Sandbox",
    "SandboxArtifacts",
    "SandboxArtifactsResource",
    "SandboxCommands",
    "SandboxEnv",
    "SandboxEvent",
    "SandboxEvents",
    "SandboxExecRunner",
    "SandboxFiles",
    "SandboxLogs",
    "SandboxPreview",
    "SandboxSnapshots",
    "SandboxState",
    "SandboxTags",
    "SandboxTerminal",
    "Sandboxes",
    "StartTemplateOptions",
    "TemplateLifecycleManifest",
]
