"""Bound Computer object — all actions scoped to a single computer ID."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Union

from ..types import (
    ActionResponse,
    DirEntry,
    ExecResult,
    FileStat,
)
from ..types import (
    Computer as ComputerModel,
)
from .agent import AgentResource, AsyncAgentResource
from .checkpoints import AsyncCheckpoints, Checkpoints
from .computer_extras import (
    AsyncComputerAutoStop,
    AsyncComputerEnv,
    AsyncComputerInbox,
    AsyncComputerLogs,
    AsyncComputerMetrics,
    AsyncComputerOsa,
    AsyncComputerPorts,
    AsyncComputerTerminal,
    AsyncComputerVolumes,
    ComputerAutoStop,
    ComputerEnv,
    ComputerInbox,
    ComputerLogs,
    ComputerMetrics,
    ComputerOsa,
    ComputerPorts,
    ComputerTerminal,
    ComputerVolumes,
)
from .connectors import AsyncComputerConnectors, ComputerConnectors
from .custom_domains import AsyncCustomDomains, CustomDomains
from .desktop import AsyncDesktopMixin, DesktopMixin
from .egress_audit import AsyncComputerAudit, ComputerAudit
from .egress_network import AsyncComputerNetwork, ComputerNetwork
from .egress_secrets import AsyncComputerSecrets, ComputerSecrets
from .events import AsyncEvents, Events
from .exec import AsyncExecResource, ExecResource
from .files import AsyncFilesResource, FilesResource
from .network_policy import AsyncNetworkPolicy, NetworkPolicy
from .services import AsyncServices, Services

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


# ───────────────────────────────────────────────────────────────────────────
# ScopedFs — file ops rooted at a fixed working directory
# ───────────────────────────────────────────────────────────────────────────

def _resolve(working_dir: str, path: str) -> str:
    if path.startswith("/"):
        return path
    prefix = working_dir if working_dir != "/" else ""
    prefix = prefix.rstrip("/") if working_dir != "/" else working_dir
    joined = f"{prefix}/{path}" if prefix else f"/{path}"
    while "/./" in joined:
        joined = joined.replace("/./", "/")
    while "//" in joined:
        joined = joined.replace("//", "/")
    return joined


class ScopedFs:
    """Thin wrapper around :class:`FilesResource` rooted at a working dir.

    Obtained via :meth:`Computer.fs`::

        fs = computer.fs("/workspace")
        fs.write_file("main.py", "print('hi')")
        source = fs.read_file("main.py")
    """

    def __init__(self, files: FilesResource, working_dir: str) -> None:
        self._files = files
        self._working_dir = (
            working_dir if working_dir == "/" else working_dir.rstrip("/")
        )

    def _r(self, path: str) -> str:
        return _resolve(self._working_dir, path)

    def write_file(self, path: str, content: Union[str, bytes]) -> None:
        self._files.write_file(self._r(path), content)

    def read_file(self, path: str) -> str:
        return self._files.read_file(self._r(path))

    def readdir(self, path: str) -> List[DirEntry]:
        return self._files.readdir(self._r(path))

    def stat(self, path: str) -> FileStat:
        return self._files.stat(self._r(path))

    def mkdir(
        self,
        path: str,
        *,
        recursive: bool = True,
        mode: Optional[Union[int, str]] = None,
    ) -> None:
        self._files.mkdir(self._r(path), recursive=recursive, mode=mode)

    def rename(self, source: str, dest: str) -> None:
        self._files.rename(self._r(source), self._r(dest))

    def copy(self, source: str, dest: str, *, recursive: bool = False) -> None:
        self._files.copy(self._r(source), self._r(dest), recursive=recursive)

    def chmod(self, path: str, mode: Union[int, str]) -> None:
        self._files.chmod(self._r(path), mode)


class AsyncScopedFs:
    """Async counterpart to :class:`ScopedFs`."""

    def __init__(self, files: AsyncFilesResource, working_dir: str) -> None:
        self._files = files
        self._working_dir = (
            working_dir if working_dir == "/" else working_dir.rstrip("/")
        )

    def _r(self, path: str) -> str:
        return _resolve(self._working_dir, path)

    async def write_file(self, path: str, content: Union[str, bytes]) -> None:
        await self._files.write_file(self._r(path), content)

    async def read_file(self, path: str) -> str:
        return await self._files.read_file(self._r(path))

    async def readdir(self, path: str) -> List[DirEntry]:
        return await self._files.readdir(self._r(path))

    async def stat(self, path: str) -> FileStat:
        return await self._files.stat(self._r(path))

    async def mkdir(
        self,
        path: str,
        *,
        recursive: bool = True,
        mode: Optional[Union[int, str]] = None,
    ) -> None:
        await self._files.mkdir(self._r(path), recursive=recursive, mode=mode)

    async def rename(self, source: str, dest: str) -> None:
        await self._files.rename(self._r(source), self._r(dest))

    async def copy(
        self, source: str, dest: str, *, recursive: bool = False
    ) -> None:
        await self._files.copy(self._r(source), self._r(dest), recursive=recursive)

    async def chmod(self, path: str, mode: Union[int, str]) -> None:
        await self._files.chmod(self._r(path), mode)


# ───────────────────────────────────────────────────────────────────────────
# Computer — sync
# ───────────────────────────────────────────────────────────────────────────

class Computer(DesktopMixin):
    """A single MIOSA computer with all action methods.

    Returned by ``ComputersResource.create()`` / ``.get()`` etc.
    Provides desktop control, exec, files, checkpoints, services,
    domains, network policy, and events sub-resources.
    """

    def __init__(self, transport: SyncTransport, data: ComputerModel) -> None:
        self._transport = transport
        self._data = data
        self._computer_id = data.id

        # Sub-resources
        self.files = FilesResource(transport, self._computer_id)
        self._exec = ExecResource(transport, self._computer_id)
        self.checkpoints = Checkpoints(transport, self._computer_id)
        self.services = Services(transport, self._computer_id)
        self.domains = CustomDomains(transport, self._computer_id)
        self.network_policy = NetworkPolicy(transport, self._computer_id)
        self.events = Events(transport, self._computer_id)
        self.agent = AgentResource(transport, self._computer_id)
        self.connectors = ComputerConnectors(transport, self._computer_id)
        # Egress (security) namespaces — pre-scoped to this computer id
        self.secrets = ComputerSecrets(transport, self._computer_id)
        self.network = ComputerNetwork(transport, self._computer_id)
        self.audit = ComputerAudit(transport, self._computer_id)

        # Extended sub-resources (computer_extras)
        self.terminal = ComputerTerminal(transport, self._computer_id)
        self.osa = ComputerOsa(transport, self._computer_id)
        self.auto_stop = ComputerAutoStop(transport, self._computer_id)
        self.inbox = ComputerInbox(transport, self._computer_id)
        self.env = ComputerEnv(transport, self._computer_id)
        self.logs = ComputerLogs(transport, self._computer_id)
        self.metrics_resource = ComputerMetrics(transport, self._computer_id)
        self.ports = ComputerPorts(transport, self._computer_id)
        self.volumes = ComputerVolumes(transport, self._computer_id)

    # -- properties exposing model data --

    @property
    def id(self) -> str:
        return self._data.id

    @property
    def name(self) -> str:
        return self._data.name

    @property
    def status(self) -> str:
        return self._data.status.value

    @property
    def slug(self) -> str:
        """URL-safe slug — falls back to the raw id when unset."""
        return self._data.slug or self._data.id

    @property
    def data(self) -> ComputerModel:
        """The underlying Pydantic model."""
        return self._data

    @property
    def exec(self) -> ExecResource:
        """Command execution helper (``bash`` / ``python`` / ``spawn``)."""
        return self._exec

    def __repr__(self) -> str:
        return f"Computer(id={self.id!r}, name={self.name!r}, status={self.status!r})"

    # -- preview URLs -------------------------------------------------------

    def preview_url(self, port: int, path: str = "/") -> str:
        """Public HTTPS URL that forwards to ``port`` inside the VM.

        Example::

            computer.bash("python -m http.server 3000 &")
            url = computer.preview_url(3000)
            # => "https://3000-<slug>.sandbox.<tenant-domain>/"
        """
        p = path if path.startswith("/") else f"/{path}"
        return f"https://{port}-{self.slug}.sandbox.{self._preview_domain}{p}"

    @property
    def public_url(self) -> str:
        """Root preview URL — whatever is served on the default app port."""
        return f"https://{self.slug}.sandbox.{self._preview_domain}"

    @property
    def _preview_domain(self) -> str:
        """Tenant's preview/base domain (white-label aware).

        Uses the server-provided ``preview_domain`` so white-label tenants
        (e.g. ``cliniciq.com``) get correct URLs. Never hardcodes a domain;
        falls back to the platform default ``miosa.ai`` only when the server
        did not supply one.
        """
        return getattr(self._data, "preview_domain", None) or "miosa.ai"

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> ActionResponse:
        """Start the computer."""
        data = self._transport.request(
            "POST", f"/computers/{self._computer_id}/start"
        )
        return ActionResponse.model_validate(data)

    def stop(self) -> ActionResponse:
        """Stop the computer."""
        data = self._transport.request(
            "POST", f"/computers/{self._computer_id}/stop"
        )
        return ActionResponse.model_validate(data)

    def restart(self) -> ActionResponse:
        """Restart the computer."""
        data = self._transport.request(
            "POST", f"/computers/{self._computer_id}/restart"
        )
        return ActionResponse.model_validate(data)

    def destroy(self) -> ActionResponse:
        """Permanently destroy the computer."""
        data = self._transport.request(
            "DELETE", f"/computers/{self._computer_id}"
        )
        return ActionResponse.model_validate(data)

    def refresh(self) -> Computer:
        """Re-fetch this computer's data from the API."""
        data = self._transport.request(
            "GET", f"/computers/{self._computer_id}"
        )
        self._data = ComputerModel.model_validate(data)
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
        """Run an AI agent inside this Computer."""
        body = {
            "instruction": instruction,
            "target_kind": "computer",
            "target_id": self._computer_id,
            "runtime_id": self._computer_id,
            "computer_id": self._computer_id,
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
        data = self._transport.request("POST", "/runs", json_body=body)
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            return data["data"]
        return data if isinstance(data, dict) else {}

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
        """Dispatch a prompt into this Computer through the Agent Runs API."""
        body = {
            "prompt": prompt,
            "target_kind": "computer",
            "target_id": self._computer_id,
            "computer_id": self._computer_id,
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
        data = self._transport.request("POST", "/agent-runs", json_body=body)
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            return data["data"]
        return data if isinstance(data, dict) else {}

    # -- exec shortcuts -----------------------------------------------------

    def bash(self, command: str, *, timeout: Optional[int] = None) -> ExecResult:
        """Execute a bash command on the computer."""
        return self._exec.bash(command, timeout=timeout)

    def run(self, command: str, *, timeout: Optional[int] = None) -> ExecResult:
        """Execute a shell command.

        Alias for :meth:`bash`, matching the simple sandbox SDK pattern used by
        Hugging Face and Modal-style examples.
        """
        return self.bash(command, timeout=timeout)

    def python(self, code: str, *, timeout: Optional[int] = None) -> ExecResult:
        """Execute Python code on the computer."""
        return self._exec.python(code, timeout=timeout)

    # -- file shortcuts -----------------------------------------------------

    def write_file(self, path: str, content: Union[str, bytes]) -> None:
        """Write bytes or UTF-8 text to a file inside the computer."""
        self.files.write_file(path, content)

    def read_file(self, path: str) -> str:
        """Read a file from the computer and decode it as UTF-8."""
        return self.files.read_file(path)

    # -- scoped filesystem --------------------------------------------------

    def fs(self, working_dir: str) -> ScopedFs:
        """Return a :class:`ScopedFs` rooted at ``working_dir``.

        Example::

            fs = computer.fs("/workspace")
            fs.write_file("main.py", "print(1)")
            src = fs.read_file("main.py")
        """
        return ScopedFs(self.files, working_dir)

    # -- single-method endpoints --------------------------------------------

    def vnc_credentials(self) -> dict:
        """Return the VNC password / connection info for this computer."""
        data = self._transport.request(
            "GET", f"/computers/{self._computer_id}/vnc-credentials"
        )
        if isinstance(data, dict) and "data" in data and len(data) <= 2:
            return data["data"]
        return data

    def viewer_password(self) -> dict:
        """Return whether the external/raw desktop viewer password is set.

        Authenticated MIOSA platform users should use the platform desktop
        entry URL and do not need this password. This is for raw external
        viewer links such as ``*.computer.miosa.ai/desktop/index.html``.
        """
        data = self._transport.request(
            "GET", f"/computers/{self._computer_id}/viewer-password"
        )
        if isinstance(data, dict) and "data" in data and len(data) <= 2:
            return data["data"]
        return data if isinstance(data, dict) else {}

    def rotate_viewer_password(self) -> dict:
        """Rotate and return the external/raw desktop viewer password once."""
        data = self._transport.request(
            "POST", f"/computers/{self._computer_id}/viewer-password/rotate"
        )
        if isinstance(data, dict) and "data" in data and len(data) <= 2:
            return data["data"]
        return data if isinstance(data, dict) else {}

    def apps(self) -> list:
        """List apps installed inside the computer."""
        data = self._transport.request(
            "GET", f"/computers/{self._computer_id}/apps"
        )
        if isinstance(data, dict):
            for key in ("data", "apps", "items"):
                value = data.get(key)
                if isinstance(value, list):
                    return value
        return data if isinstance(data, list) else []

    def urls(self) -> list:
        """List the public preview / exposed URLs for this computer."""
        data = self._transport.request(
            "GET", f"/computers/{self._computer_id}/urls"
        )
        if isinstance(data, dict):
            for key in ("data", "urls", "items"):
                value = data.get(key)
                if isinstance(value, list):
                    return value
        return data if isinstance(data, list) else []

    def stream_token(self) -> dict:
        """Mint a short-lived token for the pixel-stream protocol."""
        data = self._transport.request(
            "POST", f"/computers/{self._computer_id}/stream-token"
        )
        if isinstance(data, dict) and "data" in data and len(data) <= 2:
            return data["data"]
        return data

    def embed(self) -> dict:
        """Mint a passwordless browser embed URL for authenticated sessions.

        Use this inside MIOSA or tenant apps. Raw shared desktop URLs can still
        use the viewer password flow when opened outside an authenticated
        platform.
        """
        data = self._transport.request("GET", f"/computers/{self._computer_id}/embed")
        if isinstance(data, dict) and "data" in data and len(data) <= 2:
            return data["data"]
        return data if isinstance(data, dict) else {}

    def metrics(self, window: str = "1h") -> dict:
        """Shortcut for :attr:`metrics_resource`.get() — read time-series metrics."""
        return self.metrics_resource.get(window)

    # -- screenshot region ---------------------------------------------------

    def screenshot_region(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> bytes:
        """Capture a region of the desktop and return PNG bytes."""
        response = self._transport.request(
            "POST",
            f"/computers/{self._computer_id}/desktop/screenshot/region",
            json_body={"x": x, "y": y, "width": width, "height": height},
            raw_response=True,
        )
        body: bytes = response.content
        from ..errors import raise_for_status
        raise_for_status(
            response.status_code,
            response.text,
            response.headers.get("x-request-id"),
        )
        return body

    # -- lifecycle extensions ------------------------------------------------

    def clone(self, **opts) -> Computer:
        """Clone this computer. Returns the new :class:`Computer`."""
        body = {k: v for k, v in opts.items() if v is not None}
        raw = self._transport.request(
            "POST", f"/computers/{self._computer_id}/clone", json_body=body
        )
        comp_data = raw.get("data") if isinstance(raw, dict) and "data" in raw else raw
        model = ComputerModel.model_validate(comp_data)
        return Computer(self._transport, model)

    def resize(self, size: Optional[str] = None, **opts) -> Computer:
        """Resize the underlying VM (CPU/RAM bundle).

        Accepts either a bundle slug (``"small"``, ``"large"``, ...) via
        ``size`` or explicit ``cpu_count`` / ``memory_mb`` kwargs.
        """
        body = {k: v for k, v in opts.items() if v is not None}
        if size is not None:
            body["size"] = size
        raw = self._transport.request(
            "POST", f"/computers/{self._computer_id}/resize", json_body=body
        )
        comp_data = raw.get("data") if isinstance(raw, dict) and "data" in raw else raw
        if isinstance(comp_data, dict) and "id" in comp_data:
            self._data = ComputerModel.model_validate(comp_data)
        return self

    def move(
        self,
        *,
        host_id: Optional[str] = None,
        region: Optional[str] = None,
        **opts,
    ) -> Computer:
        """Relocate this computer to a different host/region."""
        body = {
            k: v for k, v in {
                "host_id": host_id,
                "region": region,
                **opts,
            }.items() if v is not None
        }
        raw = self._transport.request(
            "POST", f"/computers/{self._computer_id}/move", json_body=body
        )
        comp_data = raw.get("data") if isinstance(raw, dict) and "data" in raw else raw
        if isinstance(comp_data, dict) and "id" in comp_data:
            self._data = ComputerModel.model_validate(comp_data)
        return self

    # -- volume convenience shortcuts ----------------------------------------

    def list_volumes(self) -> list:
        """Shortcut for :attr:`volumes`.list() — attached volume records."""
        return self.volumes.list()

    def attach_volume(self, volume_id: str, mount_path: str) -> dict:
        """Shortcut for :attr:`volumes`.attach()."""
        return self.volumes.attach(volume_id, mount_path)

    def detach_volume(self, attachment_id: str) -> None:
        """Shortcut for :attr:`volumes`.detach()."""
        self.volumes.detach(attachment_id)


# ───────────────────────────────────────────────────────────────────────────
# AsyncComputer
# ───────────────────────────────────────────────────────────────────────────

class AsyncComputer(AsyncDesktopMixin):
    """Async version of the bound Computer object."""

    def __init__(self, transport: AsyncTransport, data: ComputerModel) -> None:
        self._transport = transport
        self._data = data
        self._computer_id = data.id

        self.files = AsyncFilesResource(transport, self._computer_id)
        self._exec = AsyncExecResource(transport, self._computer_id)
        self.checkpoints = AsyncCheckpoints(transport, self._computer_id)
        self.services = AsyncServices(transport, self._computer_id)
        self.domains = AsyncCustomDomains(transport, self._computer_id)
        self.network_policy = AsyncNetworkPolicy(transport, self._computer_id)
        self.events = AsyncEvents(transport, self._computer_id)
        self.agent = AsyncAgentResource(transport, self._computer_id)
        self.connectors = AsyncComputerConnectors(transport, self._computer_id)
        # Egress (security) namespaces — pre-scoped to this computer id
        self.secrets = AsyncComputerSecrets(transport, self._computer_id)
        self.network = AsyncComputerNetwork(transport, self._computer_id)
        self.audit = AsyncComputerAudit(transport, self._computer_id)

        # Extended sub-resources (computer_extras)
        self.terminal = AsyncComputerTerminal(transport, self._computer_id)
        self.osa = AsyncComputerOsa(transport, self._computer_id)
        self.auto_stop = AsyncComputerAutoStop(transport, self._computer_id)
        self.inbox = AsyncComputerInbox(transport, self._computer_id)
        self.env = AsyncComputerEnv(transport, self._computer_id)
        self.logs = AsyncComputerLogs(transport, self._computer_id)
        self.metrics_resource = AsyncComputerMetrics(transport, self._computer_id)
        self.ports = AsyncComputerPorts(transport, self._computer_id)
        self.volumes = AsyncComputerVolumes(transport, self._computer_id)

    @property
    def id(self) -> str:
        return self._data.id

    @property
    def name(self) -> str:
        return self._data.name

    @property
    def status(self) -> str:
        return self._data.status.value

    @property
    def slug(self) -> str:
        return self._data.slug or self._data.id

    @property
    def data(self) -> ComputerModel:
        return self._data

    @property
    def exec(self) -> AsyncExecResource:
        return self._exec

    def __repr__(self) -> str:
        return f"AsyncComputer(id={self.id!r}, name={self.name!r}, status={self.status!r})"

    def preview_url(self, port: int, path: str = "/") -> str:
        p = path if path.startswith("/") else f"/{path}"
        return f"https://{port}-{self.slug}.sandbox.{self._preview_domain}{p}"

    @property
    def public_url(self) -> str:
        return f"https://{self.slug}.sandbox.{self._preview_domain}"

    @property
    def _preview_domain(self) -> str:
        """Tenant's preview/base domain (white-label aware); server-provided,
        falls back to the platform default ``miosa.ai`` only if absent."""
        return getattr(self._data, "preview_domain", None) or "miosa.ai"

    async def start(self) -> ActionResponse:
        data = await self._transport.request(
            "POST", f"/computers/{self._computer_id}/start"
        )
        return ActionResponse.model_validate(data)

    async def stop(self) -> ActionResponse:
        data = await self._transport.request(
            "POST", f"/computers/{self._computer_id}/stop"
        )
        return ActionResponse.model_validate(data)

    async def restart(self) -> ActionResponse:
        data = await self._transport.request(
            "POST", f"/computers/{self._computer_id}/restart"
        )
        return ActionResponse.model_validate(data)

    async def destroy(self) -> ActionResponse:
        data = await self._transport.request(
            "DELETE", f"/computers/{self._computer_id}"
        )
        return ActionResponse.model_validate(data)

    async def refresh(self) -> AsyncComputer:
        data = await self._transport.request(
            "GET", f"/computers/{self._computer_id}"
        )
        self._data = ComputerModel.model_validate(data)
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
        """Run an AI agent inside this Computer."""
        body = {
            "instruction": instruction,
            "target_kind": "computer",
            "target_id": self._computer_id,
            "runtime_id": self._computer_id,
            "computer_id": self._computer_id,
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
        data = await self._transport.request("POST", "/runs", json_body=body)
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            return data["data"]
        return data if isinstance(data, dict) else {}

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
        """Dispatch a prompt into this Computer through the Agent Runs API."""
        body = {
            "prompt": prompt,
            "target_kind": "computer",
            "target_id": self._computer_id,
            "computer_id": self._computer_id,
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
        data = await self._transport.request("POST", "/agent-runs", json_body=body)
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            return data["data"]
        return data if isinstance(data, dict) else {}

    async def bash(self, command: str, *, timeout: Optional[int] = None) -> ExecResult:
        return await self._exec.bash(command, timeout=timeout)

    async def run(self, command: str, *, timeout: Optional[int] = None) -> ExecResult:
        return await self.bash(command, timeout=timeout)

    async def python(self, code: str, *, timeout: Optional[int] = None) -> ExecResult:
        return await self._exec.python(code, timeout=timeout)

    async def write_file(self, path: str, content: Union[str, bytes]) -> None:
        await self.files.write_file(path, content)

    async def read_file(self, path: str) -> str:
        return await self.files.read_file(path)

    def fs(self, working_dir: str) -> AsyncScopedFs:
        return AsyncScopedFs(self.files, working_dir)

    # -- single-method endpoints --------------------------------------------

    async def vnc_credentials(self) -> dict:
        """Return the VNC password / connection info for this computer."""
        data = await self._transport.request(
            "GET", f"/computers/{self._computer_id}/vnc-credentials"
        )
        if isinstance(data, dict) and "data" in data and len(data) <= 2:
            return data["data"]
        return data

    async def viewer_password(self) -> dict:
        """Return whether the external/raw desktop viewer password is set."""
        data = await self._transport.request(
            "GET", f"/computers/{self._computer_id}/viewer-password"
        )
        if isinstance(data, dict) and "data" in data and len(data) <= 2:
            return data["data"]
        return data if isinstance(data, dict) else {}

    async def rotate_viewer_password(self) -> dict:
        """Rotate and return the external/raw desktop viewer password once."""
        data = await self._transport.request(
            "POST", f"/computers/{self._computer_id}/viewer-password/rotate"
        )
        if isinstance(data, dict) and "data" in data and len(data) <= 2:
            return data["data"]
        return data if isinstance(data, dict) else {}

    async def apps(self) -> list:
        """List apps installed inside the computer."""
        data = await self._transport.request(
            "GET", f"/computers/{self._computer_id}/apps"
        )
        if isinstance(data, dict):
            for key in ("data", "apps", "items"):
                value = data.get(key)
                if isinstance(value, list):
                    return value
        return data if isinstance(data, list) else []

    async def urls(self) -> list:
        """List the public preview / exposed URLs for this computer."""
        data = await self._transport.request(
            "GET", f"/computers/{self._computer_id}/urls"
        )
        if isinstance(data, dict):
            for key in ("data", "urls", "items"):
                value = data.get(key)
                if isinstance(value, list):
                    return value
        return data if isinstance(data, list) else []

    async def stream_token(self) -> dict:
        """Mint a short-lived token for the pixel-stream protocol."""
        data = await self._transport.request(
            "POST", f"/computers/{self._computer_id}/stream-token"
        )
        if isinstance(data, dict) and "data" in data and len(data) <= 2:
            return data["data"]
        return data

    async def embed(self) -> dict:
        """Mint a passwordless browser embed URL for authenticated sessions."""
        data = await self._transport.request("GET", f"/computers/{self._computer_id}/embed")
        if isinstance(data, dict) and "data" in data and len(data) <= 2:
            return data["data"]
        return data if isinstance(data, dict) else {}

    async def metrics(self, window: str = "1h") -> dict:
        """Shortcut for :attr:`metrics_resource`.get()."""
        return await self.metrics_resource.get(window)

    async def screenshot_region(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> bytes:
        """Capture a region of the desktop and return PNG bytes."""
        response = await self._transport.request(
            "POST",
            f"/computers/{self._computer_id}/desktop/screenshot/region",
            json_body={"x": x, "y": y, "width": width, "height": height},
            raw_response=True,
        )
        body: bytes = response.content
        from ..errors import raise_for_status
        raise_for_status(
            response.status_code,
            response.text,
            response.headers.get("x-request-id"),
        )
        return body

    async def clone(self, **opts) -> AsyncComputer:
        """Clone this computer. Returns the new :class:`AsyncComputer`."""
        body = {k: v for k, v in opts.items() if v is not None}
        raw = await self._transport.request(
            "POST", f"/computers/{self._computer_id}/clone", json_body=body
        )
        comp_data = raw.get("data") if isinstance(raw, dict) and "data" in raw else raw
        model = ComputerModel.model_validate(comp_data)
        return AsyncComputer(self._transport, model)

    async def resize(self, size: Optional[str] = None, **opts) -> AsyncComputer:
        """Resize the VM bundle."""
        body = {k: v for k, v in opts.items() if v is not None}
        if size is not None:
            body["size"] = size
        raw = await self._transport.request(
            "POST", f"/computers/{self._computer_id}/resize", json_body=body
        )
        comp_data = raw.get("data") if isinstance(raw, dict) and "data" in raw else raw
        if isinstance(comp_data, dict) and "id" in comp_data:
            self._data = ComputerModel.model_validate(comp_data)
        return self

    async def move(
        self,
        *,
        host_id: Optional[str] = None,
        region: Optional[str] = None,
        **opts,
    ) -> AsyncComputer:
        """Relocate this computer to a different host/region."""
        body = {
            k: v for k, v in {
                "host_id": host_id,
                "region": region,
                **opts,
            }.items() if v is not None
        }
        raw = await self._transport.request(
            "POST", f"/computers/{self._computer_id}/move", json_body=body
        )
        comp_data = raw.get("data") if isinstance(raw, dict) and "data" in raw else raw
        if isinstance(comp_data, dict) and "id" in comp_data:
            self._data = ComputerModel.model_validate(comp_data)
        return self

    async def list_volumes(self) -> list:
        """Shortcut for :attr:`volumes`.list()."""
        return await self.volumes.list()

    async def attach_volume(self, volume_id: str, mount_path: str) -> dict:
        """Shortcut for :attr:`volumes`.attach()."""
        return await self.volumes.attach(volume_id, mount_path)

    async def detach_volume(self, attachment_id: str) -> None:
        """Shortcut for :attr:`volumes`.detach()."""
        await self.volumes.detach(attachment_id)
