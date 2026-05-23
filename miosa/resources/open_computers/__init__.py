"""OpenComputers namespace — BYOC host management for the MIOSA SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .agents import AgentsResource, AsyncAgentsResource
from .apps import AppsResource, AsyncAppsResource
from .clusters import AsyncClustersResource, ClustersResource
from .files import AsyncOcFilesResource, OcFilesResource
from .hosts import AsyncHostsResource, HostsResource
from .jobs import AsyncJobsResource, JobsResource
from .secrets import AsyncSecretsResource, SecretsResource
from .terminal_desktop import (
    AsyncDesktopResource,
    AsyncTerminalResource,
    DesktopResource,
    TerminalResource,
)
from .tunnels import AsyncTunnelsResource, TunnelsResource
from .workspaces import AsyncOcWorkspacesResource, OcWorkspacesResource

if TYPE_CHECKING:
    from ..._http import AsyncTransport, SyncTransport


class OpenComputers:
    """Synchronous OpenComputers namespace.

    Access via ``client.open_computers``:

    .. code-block:: python

        from miosa import Miosa
        from miosa.resources.open_computers.types import HostCreateParams, JobRunParams, TunnelCreateParams

        client = Miosa(api_key="msk_u_...")

        # Register a host
        host = client.open_computers.hosts.create(
            HostCreateParams(name="my-mac")
        )
        print(host.host_key)  # save this!

        # Run a command
        job = client.open_computers.jobs.run(
            host.id, JobRunParams(command="npm test")
        )
        for event in client.open_computers.jobs.stream(host.id, job.id):
            print(event.type, event.data)

        # Expose a port
        tunnel = client.open_computers.tunnels.create(
            host.id, TunnelCreateParams(target_port=3000)
        )
        print(tunnel.public_url)
    """

    def __init__(self, transport: "SyncTransport") -> None:
        self.hosts = HostsResource(transport)
        self.jobs = JobsResource(transport)
        self.files = OcFilesResource(transport)
        self.terminal = TerminalResource(transport)
        self.desktop = DesktopResource(transport)
        self.tunnels = TunnelsResource(transport)
        self.agents = AgentsResource(transport)
        self.clusters = ClustersResource(transport)
        self.apps = AppsResource(transport)
        self.workspaces = OcWorkspacesResource(transport)
        self.secrets = SecretsResource(transport)


class AsyncOpenComputers:
    """Asynchronous OpenComputers namespace.

    Access via ``client.open_computers``:

    .. code-block:: python

        from miosa import AsyncMiosa
        from miosa.resources.open_computers.types import HostCreateParams, JobRunParams

        async with AsyncMiosa(api_key="msk_u_...") as client:
            host = await client.open_computers.hosts.create(
                HostCreateParams(name="my-mac")
            )
            job = await client.open_computers.jobs.run(
                host.id, JobRunParams(command="npm test")
            )
            async for event in await client.open_computers.jobs.stream(host.id, job.id):
                print(event.type, event.data)
    """

    def __init__(self, transport: "AsyncTransport") -> None:
        self.hosts = AsyncHostsResource(transport)
        self.jobs = AsyncJobsResource(transport)
        self.files = AsyncOcFilesResource(transport)
        self.terminal = AsyncTerminalResource(transport)
        self.desktop = AsyncDesktopResource(transport)
        self.tunnels = AsyncTunnelsResource(transport)
        self.agents = AsyncAgentsResource(transport)
        self.clusters = AsyncClustersResource(transport)
        self.apps = AsyncAppsResource(transport)
        self.workspaces = AsyncOcWorkspacesResource(transport)
        self.secrets = AsyncSecretsResource(transport)


__all__ = [
    "OpenComputers",
    "AsyncOpenComputers",
    "HostsResource",
    "AsyncHostsResource",
    "JobsResource",
    "AsyncJobsResource",
    "OcFilesResource",
    "AsyncOcFilesResource",
    "TerminalResource",
    "AsyncTerminalResource",
    "DesktopResource",
    "AsyncDesktopResource",
    "TunnelsResource",
    "AsyncTunnelsResource",
    "AgentsResource",
    "AsyncAgentsResource",
    "ClustersResource",
    "AsyncClustersResource",
    "AppsResource",
    "AsyncAppsResource",
    "OcWorkspacesResource",
    "AsyncOcWorkspacesResource",
    "SecretsResource",
    "AsyncSecretsResource",
]
