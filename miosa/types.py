"""Pydantic v2 models for MIOSA API request and response types."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ComputerSize(str, Enum):
    XS = "xs"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XL = "xl"


class ComputerStatus(str, Enum):
    CREATING = "creating"
    PROVISIONING = "provisioning"
    STARTING = "starting"
    # `running` is the documented state; `active` is the legacy value the
    # server still emits for a running VM. Accept both — clients should
    # treat them as equivalent.
    RUNNING = "running"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    DESTROYING = "destroying"
    DESTROYED = "destroyed"


class ComputerVisibility(str, Enum):
    """Controls who can access the computer's HTTP preview URL."""

    PUBLIC = "public"
    TENANT = "tenant"
    KEY = "key"


class SnapshotStatus(str, Enum):
    CREATING = "creating"
    UPLOADING = "uploading"
    READY = "ready"
    RESTORING = "restoring"
    FAILED = "failed"
    DELETED = "deleted"


class ServiceStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


class CustomDomainStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    ACTIVE = "active"
    FAILED = "failed"
    REMOVED = "removed"


class NetworkPolicyEffect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class NetworkPolicyProtocol(str, Enum):
    TCP = "tcp"
    UDP = "udp"
    ANY = "any"


class MouseButton(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class ScrollDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


class AgentSessionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Computers
# ---------------------------------------------------------------------------

class Computer(BaseModel):
    """A MIOSA computer (cloud VM for AI agents)."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    slug: Optional[str] = None
    status: ComputerStatus
    template_type: Optional[str] = Field(None, alias="template_type")
    size: Optional[ComputerSize] = None
    ip_address: Optional[str] = Field(None, alias="ip_address")
    visibility: Optional[ComputerVisibility] = None
    sandbox_url: Optional[str] = Field(None, alias="sandbox_url")
    desktop_url: Optional[str] = Field(None, alias="desktop_url")
    workspace_id: Optional[str] = Field(None, alias="workspace_id")
    tenant_id: Optional[str] = Field(None, alias="tenant_id")
    created_at: Optional[datetime] = Field(None, alias="created_at")
    updated_at: Optional[datetime] = Field(None, alias="updated_at")
    metadata: Optional[Dict[str, Any]] = None


class ComputerCreate(BaseModel):
    """Payload for creating a computer."""

    name: str
    template_type: str = "miosa-desktop"
    size: ComputerSize = ComputerSize.SMALL
    visibility: Optional[ComputerVisibility] = None
    metadata: Optional[Dict[str, Any]] = None
    # Workspace / attribution fields — all optional
    workspace_id: Optional[str] = None
    external_workspace_id: Optional[str] = None
    external_project_id: Optional[str] = None
    agent_runtime_profile_id: Optional[str] = None
    agent_profile_id: Optional[str] = None
    skip_agent_runtime_profile: Optional[bool] = None


class ComputerUpdate(BaseModel):
    """Payload for updating a computer."""

    name: Optional[str] = None
    visibility: Optional[ComputerVisibility] = None
    metadata: Optional[Dict[str, Any]] = None


class ComputerList(BaseModel):
    """Paginated list of computers."""

    data: List[Computer]
    total: Optional[int] = None


# ---------------------------------------------------------------------------
# Desktop
# ---------------------------------------------------------------------------

class ClickRequest(BaseModel):
    x: int
    y: int
    button: MouseButton = MouseButton.LEFT


class DoubleClickRequest(BaseModel):
    x: int
    y: int


class TypeRequest(BaseModel):
    text: str
    delay: Optional[int] = None


class KeyRequest(BaseModel):
    key: str


class HotkeyRequest(BaseModel):
    keys: List[str]


class KeyDownRequest(BaseModel):
    key: str


class KeyUpRequest(BaseModel):
    key: str


class ScrollRequest(BaseModel):
    direction: ScrollDirection
    clicks: int = 3
    x: Optional[int] = None
    y: Optional[int] = None


class DragRequest(BaseModel):
    from_x: int
    from_y: int
    to_x: int
    to_y: int


class MoveCursorRequest(BaseModel):
    x: int
    y: int


class MouseDownRequest(BaseModel):
    x: int
    y: int
    button: MouseButton = MouseButton.LEFT


class MouseUpRequest(BaseModel):
    x: int
    y: int
    button: MouseButton = MouseButton.LEFT


class WaitRequest(BaseModel):
    seconds: float


class WindowResizeRequest(BaseModel):
    width: int
    height: int


class WindowMoveRequest(BaseModel):
    x: int
    y: int


class LaunchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    app: str = Field(..., alias="app")

    def __init__(
        self,
        *,
        app_name: str | None = None,
        app: str | None = None,
        **data: object,
    ) -> None:
        # Accept both keyword forms: app_name="..." (SDK callers) and app="..." (direct).
        resolved = app if app is not None else app_name
        if resolved is None:
            raise ValueError("app_name (or app) is required")
        super().__init__(app=resolved, **data)

    def model_dump(self, **kwargs: object) -> dict:  # type: ignore[override]
        kwargs.setdefault("by_alias", True)
        return super().model_dump(**kwargs)


class WindowFocusRequest(BaseModel):
    window_id: str


class CursorPosition(BaseModel):
    x: int
    y: int


class ScreenSize(BaseModel):
    width: int
    height: int


class WindowInfo(BaseModel):
    id: str
    title: Optional[str] = None
    app: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    focused: Optional[bool] = None


class WindowSize(BaseModel):
    width: int
    height: int


class WindowPosition(BaseModel):
    x: int
    y: int


class DesktopEnvironment(BaseModel):
    """Desktop environment info returned by ``GET /desktop/environment``."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    name: Optional[str] = None
    """Display manager / DE name, e.g. ``"xfce"`` or ``"gnome"``."""
    session_type: Optional[str] = Field(None, alias="session_type")
    """Session protocol: ``"x11"`` or ``"wayland"``."""
    resolution: Optional[str] = None
    """Current resolution as ``"WxH"``, e.g. ``"1920x1080"``."""
    width: Optional[int] = None
    height: Optional[int] = None
    color_depth: Optional[int] = Field(None, alias="color_depth")
    display: Optional[str] = None
    """X11 DISPLAY value, e.g. ``":1"``."""


class WallpaperRequest(BaseModel):
    """Payload for ``POST /desktop/wallpaper``."""

    path: str
    """Absolute VM path or ``https://`` URL to the wallpaper image."""


# ---------------------------------------------------------------------------
# Exec
# ---------------------------------------------------------------------------

class ExecRequest(BaseModel):
    command: str
    timeout: Optional[int] = None


class PythonExecRequest(BaseModel):
    code: str
    timeout: Optional[int] = None


class ExecResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    exit_code: int = 0
    output: str = ""
    success: bool = True
    stderr: str = ""

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if "stdout" in values and "output" not in values:
                values["output"] = values.pop("stdout")
            if "exit_code" in values and "success" not in values:
                values["success"] = values["exit_code"] == 0
        return values

    @property
    def stdout(self) -> str:
        return self.output


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

class FileInfo(BaseModel):
    name: str
    path: str
    size: Optional[int] = None
    is_dir: bool = Field(False, alias="is_dir")
    modified_at: Optional[datetime] = Field(None, alias="modified_at")

    model_config = ConfigDict(populate_by_name=True)


class FileList(BaseModel):
    data: List[FileInfo]


# ---------------------------------------------------------------------------
# Computer control sessions
# ---------------------------------------------------------------------------

class AgentSessionCreate(BaseModel):
    goal: str
    model_id: Optional[str] = None
    max_turns: Optional[int] = None


class AgentSession(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    computer_id: Optional[str] = Field(None, alias="computer_id")
    goal: str
    status: AgentSessionStatus
    model_id: Optional[str] = Field(None, alias="model_id")
    max_turns: Optional[int] = Field(None, alias="max_turns")
    turns_used: Optional[int] = Field(None, alias="turns_used")
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = Field(None, alias="created_at")
    updated_at: Optional[datetime] = Field(None, alias="updated_at")


class AgentSessionList(BaseModel):
    data: List[AgentSession]


class AgentEvent(BaseModel):
    """A single SSE event from an agent session stream."""

    type: str
    data: Any = None
    id: Optional[str] = None


# ---------------------------------------------------------------------------
# Credits / Billing
# ---------------------------------------------------------------------------

class CreditBalance(BaseModel):
    # The platform API returns `balance_credits` (integer) + lifetime totals.
    # Accept both `balance_credits` and the legacy `balance` shape so older
    # test fixtures keep working.
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    balance: int = Field(alias="balance_credits")
    tenant_id: Optional[str] = None
    lifetime_earned: Optional[int] = None
    lifetime_spent: Optional[int] = None
    credit_expiry_at: Optional[datetime] = Field(None, alias="credit_expiry_at")
    updated_at: Optional[datetime] = Field(None, alias="updated_at")
    # Legacy optional fields kept for backwards compatibility.
    currency: Optional[str] = None
    plan: Optional[str] = None
    expires_at: Optional[datetime] = None


class CreditTransaction(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    amount: float
    type: str
    description: Optional[str] = None
    created_at: Optional[datetime] = Field(None, alias="created_at")


class CreditTransactionList(BaseModel):
    data: List[CreditTransaction]


class CreditUsage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    compute: Optional[float] = None
    ai: Optional[float] = None
    storage: Optional[float] = None
    total: Optional[float] = None
    period_start: Optional[datetime] = Field(None, alias="period_start")
    period_end: Optional[datetime] = Field(None, alias="period_end")


# ---------------------------------------------------------------------------
# Generic
# ---------------------------------------------------------------------------

class ActionResponse(BaseModel):
    """Generic action response (start, stop, restart, etc.)."""

    success: bool = True
    message: Optional[str] = None
    status: Optional[str] = None


# ---------------------------------------------------------------------------
# Filesystem (stdlib-parity)
# ---------------------------------------------------------------------------

class FileStat(BaseModel):
    """Stat info for a file — mirrors the TS ``FileStat`` shape."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    path: str
    size: int
    mode: int
    is_dir: bool = Field(alias="is_dir")
    is_symlink: bool = Field(alias="is_symlink")
    symlink_target: Optional[str] = Field(None, alias="symlink_target")
    modified_at: Optional[datetime] = Field(None, alias="modified_at")


class DirEntry(BaseModel):
    """A single entry in a ``readdir`` listing."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str
    is_dir: bool = Field(alias="is_dir")
    is_symlink: bool = Field(alias="is_symlink")
    size: int = 0
    modified_at: Optional[datetime] = Field(None, alias="modified_at")


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------

class WorkspaceData(BaseModel):
    """A tenant workspace — a logical grouping of computers."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str
    name: str
    slug: Optional[str] = None
    tenant_id: Optional[str] = Field(None, alias="tenant_id")
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = Field(None, alias="created_at")
    updated_at: Optional[datetime] = Field(None, alias="updated_at")

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


class WorkspaceCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Checkpoints / Snapshots
# ---------------------------------------------------------------------------

class SnapshotData(BaseModel):
    """A Firecracker microVM checkpoint."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str
    computer_id: str = Field(alias="computer_id")
    tenant_id: Optional[str] = Field(None, alias="tenant_id")
    comment: Optional[str] = None
    status: SnapshotStatus
    state_size_bytes: Optional[int] = Field(None, alias="state_size_bytes")
    memory_size_bytes: Optional[int] = Field(None, alias="memory_size_bytes")
    rootfs_size_bytes: Optional[int] = Field(None, alias="rootfs_size_bytes")
    compressed_size_bytes: Optional[int] = Field(None, alias="compressed_size_bytes")
    s3_bucket: Optional[str] = Field(None, alias="s3_bucket")
    s3_prefix: Optional[str] = Field(None, alias="s3_prefix")
    parent_snapshot_id: Optional[str] = Field(None, alias="parent_snapshot_id")
    error: Optional[str] = None
    created_at: Optional[datetime] = Field(None, alias="created_at")
    updated_at: Optional[datetime] = Field(None, alias="updated_at")


class SnapshotProgressEvent(BaseModel):
    """SSE progress event emitted during checkpoint create/restore."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    type: str = "snapshot_progress"
    snapshot_id: str = Field(alias="snapshot_id")
    status: str
    step: Optional[str] = None
    progress: Optional[float] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

class ServiceData(BaseModel):
    """A long-running background service managed by the platform."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str
    computer_id: str = Field(alias="computer_id")
    name: str
    command: str
    status: ServiceStatus
    working_dir: Optional[str] = Field(None, alias="working_dir")
    env: Optional[Dict[str, str]] = None
    restart_policy: Optional[str] = Field(None, alias="restart_policy")
    port: Optional[int] = None
    pid: Optional[int] = None
    exit_code: Optional[int] = Field(None, alias="exit_code")
    created_at: Optional[datetime] = Field(None, alias="created_at")
    updated_at: Optional[datetime] = Field(None, alias="updated_at")


class ServiceLogEvent(BaseModel):
    """A single log line emitted by a service."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    stream: str  # "stdout" | "stderr"
    line: str
    timestamp: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Custom Domains
# ---------------------------------------------------------------------------

class CustomDomainData(BaseModel):
    """A custom FQDN mapped to a computer."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str
    computer_id: str = Field(alias="computer_id")
    tenant_id: Optional[str] = Field(None, alias="tenant_id")
    fqdn: str
    status: CustomDomainStatus
    verification_target: Optional[str] = Field(None, alias="verification_target")
    instructions: Optional[str] = None
    verified_at: Optional[datetime] = Field(None, alias="verified_at")
    tls_issued_at: Optional[datetime] = Field(None, alias="tls_issued_at")
    created_at: Optional[datetime] = Field(None, alias="created_at")
    updated_at: Optional[datetime] = Field(None, alias="updated_at")


# ---------------------------------------------------------------------------
# Network Policy
# ---------------------------------------------------------------------------

class NetworkPolicyRule(BaseModel):
    """A single egress rule."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    effect: NetworkPolicyEffect
    destination: str
    ports: Optional[str] = None
    protocol: Optional[NetworkPolicyProtocol] = None


class NetworkPolicyData(BaseModel):
    """The current egress policy applied to a computer."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    computer_id: Optional[str] = Field(None, alias="computer_id")
    tenant_id: Optional[str] = Field(None, alias="tenant_id")
    rules: List[NetworkPolicyRule] = Field(default_factory=list)
    default_effect: NetworkPolicyEffect = Field(
        NetworkPolicyEffect.ALLOW, alias="default_effect"
    )
    inserted_at: Optional[datetime] = Field(None, alias="inserted_at")
    updated_at: Optional[datetime] = Field(None, alias="updated_at")


class NetworkPolicySet(BaseModel):
    """Payload for ``PUT /computers/:id/network-policy``."""

    model_config = ConfigDict(populate_by_name=True)

    rules: List[NetworkPolicyRule]
    default_effect: Optional[NetworkPolicyEffect] = Field(
        None, alias="default_effect"
    )


# ---------------------------------------------------------------------------
# Events (real-time subscription)
# ---------------------------------------------------------------------------

class ComputerEvent(BaseModel):
    """A single typed event emitted by the in-VM event stream."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    type: str
    timestamp: Optional[datetime] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# White-label attribution
# ---------------------------------------------------------------------------
#
# Optional external IDs supplied by platforms embedding MIOSA. Stored as text
# alongside resources and events; tenant_id is the only thing that
# authorizes. See docs/platform/attribution.
# ---------------------------------------------------------------------------


class ExternalAttribution(BaseModel):
    """Optional external IDs for white-label resource grouping.

    These never authorize anything. They group/filter inside the tenant
    derived from the API key. Backed by the Phase 2A migration on the
    backend (Engine.ExternalAttribution helper).
    """

    model_config = ConfigDict(populate_by_name=True)

    external_workspace_id: Optional[str] = None
    external_user_id: Optional[str] = None
    external_project_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Deployments
# ---------------------------------------------------------------------------


class DeploymentState(str, Enum):
    PENDING = "pending"
    BUILDING = "building"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


class DeploymentVersionKind(str, Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"
    SANDBOX_BACKED = "sandbox_backed"


class DeploymentVersionState(str, Enum):
    CREATED = "created"
    BUILDING = "building"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"


class DeploymentSourceType(str, Enum):
    REPO = "repo"
    SANDBOX = "sandbox"
    UPLOAD = "upload"


class DeploymentServiceType(str, Enum):
    STATIC_WEB = "static_web"
    WEB = "web"
    API = "api"
    FUNCTION = "function"
    WORKER = "worker"
    CRON = "cron"
    POSTGRES = "postgres"
    REDIS = "redis"
    BUCKET = "bucket"
    VOLUME = "volume"


class RuntimeInstanceState(str, Enum):
    PROVISIONING = "provisioning"
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    ERROR = "error"
    STOPPED = "stopped"
    DESTROYED = "destroyed"


class DockerDeployHostStatus(str, Enum):
    PENDING = "pending"
    PROVISIONING = "provisioning"
    BOOTSTRAPPING = "bootstrapping"
    ACTIVE = "active"
    DEGRADED = "degraded"
    SUSPENDED = "suspended"
    RETIRED = "retired"
    ERROR = "error"


class DockerDeployApplianceStatus(str, Enum):
    NOT_INSTALLED = "not_installed"
    INSTALLING = "installing"
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class DockerDeployHost(BaseModel):
    """Dedicated workspace host that runs the App Engine appliance."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    tenant_id: str
    workspace_id: str
    external_workspace_id: Optional[str] = None
    computer_id: Optional[str] = None
    fleet_node_id: Optional[str] = None
    status: DockerDeployHostStatus
    size: str
    region: str
    portal_domain: Optional[str] = None
    runtime_base_url: Optional[str] = None
    agent_base_url: Optional[str] = None
    appliance_image: Optional[str] = None
    appliance_version: Optional[str] = None
    appliance_status: DockerDeployApplianceStatus = DockerDeployApplianceStatus.NOT_INSTALLED
    agent_last_seen_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DockerDeployTemplate(BaseModel):
    """Starter template for App Engine apps and compose workloads."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    runtime: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Deployment(BaseModel):
    """Stable production object for a published app/site/API."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    tenant_id: str
    owner_id: Optional[str] = None
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    name: str
    slug: str
    repo_url: Optional[str] = None
    repo_provider: Optional[str] = "github"
    branch: Optional[str] = "main"
    build_command: Optional[str] = None
    run_command: Optional[str] = None
    runtime_image: Optional[str] = None
    current_build_id: Optional[str] = None
    active_version_id: Optional[str] = None
    active_release_id: Optional[str] = None
    running_artifact_sha256: Optional[str] = None
    source_type: Optional[DeploymentSourceType] = None
    state: DeploymentState
    auto_deploy: bool = True
    custom_domain_id: Optional[str] = None
    linked_database_id: Optional[str] = None
    deployment_product: Optional[str] = None
    docker_deploy_host_id: Optional[str] = None
    docker_deploy_app: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    external_workspace_id: Optional[str] = None
    external_user_id: Optional[str] = None
    external_project_id: Optional[str] = None
    public_url: Optional[str] = None
    auto_subdomain: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DeploymentVersion(BaseModel):
    """Immutable history record of one publish."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    deployment_id: str
    tenant_id: str
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    created_by: Optional[str] = None
    source_sandbox_id: Optional[str] = None
    build_id: Optional[str] = None
    version_number: int
    kind: DeploymentVersionKind
    state: DeploymentVersionState
    artifact_uri: Optional[str] = None
    artifact_manifest: Dict[str, Any] = Field(default_factory=dict)
    artifact_sha256: Optional[str] = None
    runtime_image: Optional[str] = None
    runtime_command: Optional[str] = None
    runtime_port: Optional[int] = None
    health_check_path: Optional[str] = None
    build_log_uri: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    promoted_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    external_workspace_id: Optional[str] = None
    external_user_id: Optional[str] = None
    external_project_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DeploymentRelease(BaseModel):
    """Immutable build artifact (static tarball, OCI image, or rootfs)."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    deployment_id: Optional[str] = None
    environment_id: Optional[str] = None
    deployment_version_id: str
    service_id: Optional[str] = None
    tenant_id: str
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    external_workspace_id: Optional[str] = None
    external_user_id: Optional[str] = None
    external_project_id: Optional[str] = None
    source_sandbox_id: Optional[str] = None
    build_id: Optional[str] = None
    kind: str  # "static" | "oci" | "rootfs"
    state: Optional[str] = None
    artifact_uri: Optional[str] = None
    artifact_sha256: Optional[str] = None
    artifact_manifest: Dict[str, Any] = Field(default_factory=dict)
    storage_backend: Optional[str] = None
    storage_uri: Optional[str] = None
    sha256: Optional[str] = None
    size_bytes: Optional[int] = None
    start_command: Optional[str] = None
    port: Optional[int] = None
    health_check_path: Optional[str] = None
    build_log_uri: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ready_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DeploymentService(BaseModel):
    """One row per web/api/worker/cron/etc within a deployment."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    deployment_id: str
    environment_id: Optional[str] = None
    tenant_id: str
    type: DeploymentServiceType
    name: Optional[str] = None
    desired_replicas: int = 1
    state: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RuntimeInstance(BaseModel):
    """Running production VM serving a dynamic release."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    deployment_id: Optional[str] = None
    environment_id: Optional[str] = None
    service_id: Optional[str] = None
    release_id: Optional[str] = None
    tenant_id: str
    external_workspace_id: Optional[str] = None
    external_user_id: Optional[str] = None
    external_project_id: Optional[str] = None
    host_id: Optional[str] = None
    node_id: Optional[str] = None
    vm_id: Optional[str] = None
    desired_state: Optional[str] = None
    state: RuntimeInstanceState
    ip_address: Optional[str] = None
    port: Optional[int] = None
    health_check_path: Optional[str] = None
    last_health_check_at: Optional[datetime] = None
    last_heartbeat_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    error_message: Optional[str] = None
    restart_count: Optional[int] = None
    cpu_limit_millicores: Optional[int] = None
    memory_limit_mb: Optional[int] = None
    runtime_log_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DeploymentBuild(BaseModel):
    """A single build attempt for a deployment."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    deployment_id: str
    commit_sha: Optional[str] = None
    commit_message: Optional[str] = None
    triggered_by: Optional[str] = None
    state: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    log_url: Optional[str] = None
    image_digest: Optional[str] = None
    error_message: Optional[str] = None
    external_workspace_id: Optional[str] = None
    external_user_id: Optional[str] = None
    external_project_id: Optional[str] = None
    created_at: Optional[datetime] = None


class PublishResult(BaseModel):
    """Response shape from POST /deployments/:id/publish."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    deployment: Deployment
    version: DeploymentVersion
    release: Optional[DeploymentRelease] = None
    services: List[DeploymentService] = Field(default_factory=list)
    promoted: bool = False


# ---------------------------------------------------------------------------
# Sandbox previews (formal type — share-token aware)
# ---------------------------------------------------------------------------


class PreviewVisibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class PreviewState(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    DELETED = "deleted"


class SandboxPreviewData(BaseModel):
    """Live URL into a sandbox port."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    sandbox_id: str
    tenant_id: Optional[str] = None
    owner_id: Optional[str] = None
    name: Optional[str] = None
    port: int
    visibility: PreviewVisibility = PreviewVisibility.PUBLIC
    state: PreviewState = PreviewState.ACTIVE
    url: str
    expires_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    share_token_prefix: Optional[str] = None
    share_token_expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    external_workspace_id: Optional[str] = None
    external_user_id: Optional[str] = None
    external_project_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PreviewShareResult(BaseModel):
    """Response from POST /sandboxes/:id/previews/:preview_id/share.

    The ``preview_token`` is the raw share token, returned exactly once.
    Persist or use immediately; subsequent reads only return the prefix.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    preview: SandboxPreviewData
    preview_token: str
    share_url: str


# ---------------------------------------------------------------------------
# Egress — secrets, network, audit
# ---------------------------------------------------------------------------


class EgressSecretType(str, Enum):
    """Kind of credential held by an egress secret."""

    API_KEY = "api_key"
    OAUTH_TOKEN = "oauth_token"
    BEARER = "bearer"
    BASIC = "basic"
    GENERIC = "generic"


class EgressSecretScope(str, Enum):
    """Visibility scope for an egress secret."""

    USER = "user"
    WORKSPACE = "workspace"
    TENANT = "tenant"
    EXTERNAL_USER = "external_user"
    EXTERNAL_WORKSPACE = "external_workspace"


class EgressPolicyMode(str, Enum):
    """Egress policy enforcement mode."""

    ENFORCE = "enforce"
    AUDIT_ONLY = "audit_only"


class EgressRuleEffect(str, Enum):
    """Effect of a single allowlist rule."""

    ALLOW = "allow"
    DENY = "deny"


class EgressSecretData(BaseModel):
    """A stored egress secret. The raw ``value`` is never returned."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    name: str
    type: str = EgressSecretType.API_KEY.value
    scope: str = EgressSecretScope.USER.value
    workspace_id: Optional[str] = None
    owner_user_id: Optional[str] = None
    external_user_id: Optional[str] = None
    external_workspace_id: Optional[str] = None
    masked_value: Optional[str] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EgressBindingData(BaseModel):
    """A secret binding — exposes ``secret_id`` as ``env_var`` on a resource."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    secret_id: str
    resource_id: str
    resource_type: str
    expose_as_env: str
    created_at: Optional[datetime] = None


class EgressAllowlistRule(BaseModel):
    """A single allow/deny rule in the egress proxy allowlist."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    host: str
    effect: str = EgressRuleEffect.ALLOW.value
    methods: List[str] = Field(default_factory=list)
    path_glob: Optional[str] = None
    policy_id: Optional[str] = None
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None


class EgressPolicyData(BaseModel):
    """A named egress policy attached to one or more resources."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    name: Optional[str] = None
    mode: str = EgressPolicyMode.ENFORCE.value
    default_effect: str = EgressRuleEffect.DENY.value
    description: Optional[str] = None
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    rules: List[EgressAllowlistRule] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EgressAuditEvent(BaseModel):
    """A single row from the egress audit log."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    action: Optional[str] = None
    effect: Optional[str] = None
    host: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    status_code: Optional[int] = None
    actor_id: Optional[str] = None
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    policy_id: Optional[str] = None
    rule_id: Optional[str] = None
    external_user_id: Optional[str] = None
    external_workspace_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    inserted_at: Optional[datetime] = None


class OauthStartResult(BaseModel):
    """Response shape from ``POST /egress/oauth/start``."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    authorize_url: str
    state: str
    provider: Optional[str] = None
    expires_at: Optional[datetime] = None
