"""Pydantic models for OpenComputers request/response types."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Hosts
# ---------------------------------------------------------------------------


class HostStatus(str, Enum):
    PENDING = "pending"
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    REVOKED = "revoked"


class Host(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    region: Optional[str] = None
    status: HostStatus
    tenant_id: str
    labels: Dict[str, str] = {}
    # Only present on the create response — shown once.
    host_key: Optional[str] = None
    created_at: str
    updated_at: str


class HostListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    data: List[Host]
    meta: Dict[str, Any] = {}


class HostCreateParams(BaseModel):
    name: str
    region: Optional[str] = None
    labels: Optional[Dict[str, str]] = None


class HostUpdateParams(BaseModel):
    name: Optional[str] = None
    labels: Optional[Dict[str, str]] = None


class HostEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    host_id: str
    data: Any = None
    timestamp: str


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    host_id: str
    status: JobStatus
    command: str
    args: List[str] = []
    env: List[str] = []
    cwd: Optional[str] = None
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None


class JobListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    data: List[Job]
    meta: Dict[str, Any] = {}


class JobRunParams(BaseModel):
    command: str
    args: Optional[List[str]] = None
    env: Optional[List[str]] = None
    cwd: Optional[str] = None
    timeout: Optional[int] = None


class JobEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    job_id: str
    data: Any = None
    timestamp: str


# ---------------------------------------------------------------------------
# File system
# ---------------------------------------------------------------------------


class FsEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    path: str
    size: int
    is_dir: bool
    modified_at: str


class FsStat(BaseModel):
    model_config = ConfigDict(extra="allow")

    path: str
    size: int
    mode: int
    is_dir: bool
    is_symlink: bool
    symlink_target: Optional[str] = None
    modified_at: str


class FsListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    entries: List[FsEntry]
    path: str


# ---------------------------------------------------------------------------
# Terminal / Desktop
# ---------------------------------------------------------------------------


class WsTicket(BaseModel):
    model_config = ConfigDict(extra="allow")

    ticket: str
    ws_url: str
    expires_at: str


# ---------------------------------------------------------------------------
# Tunnels
# ---------------------------------------------------------------------------


class TunnelAuthMode(str, Enum):
    PUBLIC = "public"
    TENANT_ONLY = "tenant_only"
    PASSWORD = "password"


class Tunnel(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    host_id: str
    slug: str
    target_port: int
    auth_mode: TunnelAuthMode
    public_url: str
    enabled: bool
    created_at: str
    updated_at: str


class TunnelListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    data: List[Tunnel]


class TunnelCreateParams(BaseModel):
    target_port: int
    auth_mode: Optional[TunnelAuthMode] = None
    slug: Optional[str] = None


class TunnelUpdateParams(BaseModel):
    target_port: Optional[int] = None
    auth_mode: Optional[TunnelAuthMode] = None
    enabled: Optional[bool] = None


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


class OcAgentSessionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OcAgentSession(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    host_id: str
    task: str
    model_id: Optional[str] = None
    status: OcAgentSessionStatus
    max_turns: int
    turns_used: int
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


class OcAgentSessionListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    data: List[OcAgentSession]


class AgentDispatchParams(BaseModel):
    task: str
    model_id: Optional[str] = None
    max_turns: Optional[int] = None
    context: Optional[Dict[str, Any]] = None


class OcAgentEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    session_id: str
    data: Any = None
    timestamp: str


# ---------------------------------------------------------------------------
# Inference Clusters
# ---------------------------------------------------------------------------


class ClusterStatus(str, Enum):
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    STOPPED = "stopped"
    ERROR = "error"
    DESTROYED = "destroyed"


class Cluster(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    model: str
    slug: str
    status: ClusterStatus
    host_ids: List[str]
    inference_url: str
    created_at: str
    updated_at: str


class ClusterListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    data: List[Cluster]


class ClusterCreateParams(BaseModel):
    name: str
    model: str
    host_ids: List[str]


class ClusterEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    cluster_id: str
    data: Any = None
    timestamp: str


# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------


class AppCatalogEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    description: str
    category: str
    version: str
    icon_url: Optional[str] = None


class AppInstallStatus(str, Enum):
    PENDING = "pending"
    INSTALLING = "installing"
    INSTALLED = "installed"
    FAILED = "failed"
    UNINSTALLED = "uninstalled"


class AppInstall(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    host_id: str
    app_id: str
    status: AppInstallStatus
    error: Optional[str] = None
    created_at: str
    updated_at: str


class AppInstallEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    install_id: str
    data: Any = None
    timestamp: str


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------


class OcWorkspaceStatus(str, Enum):
    CREATING = "creating"
    READY = "ready"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class OcWorkspace(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    host_id: str
    name: str
    repo_url: Optional[str] = None
    branch: Optional[str] = None
    status: OcWorkspaceStatus
    directory: str
    created_at: str
    updated_at: str


class OcWorkspaceListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    data: List[OcWorkspace]


class OcWorkspaceCreateParams(BaseModel):
    name: str
    repo_url: Optional[str] = None
    branch: Optional[str] = None
    directory: Optional[str] = None


class OcWorkspaceUpdateParams(BaseModel):
    name: Optional[str] = None
    branch: Optional[str] = None


class OcWorkspaceEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    workspace_id: str
    data: Any = None
    timestamp: str


# ---------------------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------------------


class Secret(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    description: Optional[str] = None
    host_id: Optional[str] = None
    tenant_id: str
    created_at: str
    updated_at: str


class SecretCreateParams(BaseModel):
    name: str
    value: str
    description: Optional[str] = None


class SecretUpdateParams(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None
