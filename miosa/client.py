"""Top-level Miosa and AsyncMiosa client classes."""

from __future__ import annotations

import os
from typing import Any, Optional

from ._http import DEFAULT_BASE_URL, DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT, AsyncTransport, SyncTransport
from .resources.admin import Admin, AsyncAdmin
from .resources.analytics import Analytics, AsyncAnalytics
from .resources.api_keys import ApiKeys, AsyncApiKeys
from .resources.audit_log import AsyncAuditLog, AuditLog
from .resources.benchmarks import AsyncBenchmarks, Benchmarks
from .resources.builder_sessions import AsyncBuilderSessions, BuilderSessions
from .resources.channels import AsyncChannels, Channels
from .resources.command_center import AsyncCommandCenter, CommandCenter
from .resources.community import AsyncCommunity, Community
from .resources.completions import AsyncCompletions, Completions
from .resources.computers import AsyncComputersResource, ComputersResource
from .resources.cron_jobs import AsyncCronJobs, CronJobs
from .resources.dashboard import AsyncDashboard, Dashboard
from .resources.databases import AsyncDatabases, Databases
from .resources.deployments import AsyncDeployments, Deployments
from .resources.egress_audit import AsyncEgressAudit, EgressAudit
from .resources.egress_network import AsyncEgressNetwork, EgressNetwork
from .resources.egress_secrets import AsyncEgressSecrets, EgressSecrets
from .resources.email import AsyncEmail, Email
from .resources.embeddings import AsyncEmbeddings, Embeddings
from .resources.external_keys import AsyncExternalKeys, ExternalKeys
from .resources.flat_custom_domains import AsyncFlatCustomDomains, FlatCustomDomains
from .resources.functions import AsyncFunctions, Functions
from .resources.health_checks import AsyncHealthChecks, HealthChecks
from .resources.integrations import AsyncIntegrations, Integrations
from .resources.mcp import MCP, AsyncMCP
from .resources.models import AsyncModels, Models
from .resources.open_computers import AsyncOpenComputers, OpenComputers
from .resources.project_auth import AsyncProjectAuth, ProjectAuth
from .resources.project_integrations import AsyncProjectIntegrations, ProjectIntegrations
from .resources.provider_defaults import AsyncProviderDefaults, ProviderDefaults
from .resources.regions import AsyncRegions, Regions
from .resources.sandbox_templates import AsyncSandboxTemplates, SandboxTemplates
from .resources.sandboxes import AsyncSandboxes, Sandboxes
from .resources.settings import AsyncSettings, Settings
from .resources.snapshots_standalone import AsyncSnapshotsStandalone, SnapshotsStandalone
from .resources.storage import AsyncStorage, Storage
from .resources.tenant import AsyncTenant, Tenant
from .resources.usage import AsyncUsage, Usage
from .resources.volumes import AsyncVolumes, Volumes
from .resources.webhooks import AsyncWebhooks, Webhooks
from .resources.workspaces import AsyncWorkspaces, Workspaces
from .types import CreditBalance, CreditTransactionList, CreditUsage


class Miosa:
    """Synchronous MIOSA API client.

    Usage::

        from miosa import Miosa

        client = Miosa(api_key="msk_u_...")
        computer = client.computers.create(name="my-agent")
        computer.start()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        resolved_key = api_key or os.environ.get("MIOSA_API_KEY")
        if not resolved_key:
            raise ValueError(
                "No API key provided. Pass api_key= or set the MIOSA_API_KEY "
                "environment variable."
            )

        resolved_url = base_url or os.environ.get("MIOSA_BASE_URL", DEFAULT_BASE_URL)

        self._transport = SyncTransport(
            api_key=resolved_key,
            base_url=resolved_url,
            timeout=timeout,
            max_retries=max_retries,
        )

        self.computers = ComputersResource(self._transport)
        self.sandboxes = Sandboxes(self._transport)
        self.deployments = Deployments(self._transport)
        self.workspaces = Workspaces(self._transport)
        self.admin = Admin(self._transport)
        self.open_computers = OpenComputers(self._transport)
        # P1 data + platform primitives
        self.databases = Databases(self._transport)
        self.storage = Storage(self._transport)
        self.volumes = Volumes(self._transport)
        self.custom_domains = FlatCustomDomains(self._transport)
        self.functions = Functions(self._transport)
        self.cron_jobs = CronJobs(self._transport)
        self.health_checks = HealthChecks(self._transport)
        self.webhooks = Webhooks(self._transport)
        self.sandbox_templates = SandboxTemplates(self._transport)
        self.api_keys = ApiKeys(self._transport)
        # P2 tenant + platform admin
        self.tenant = Tenant(self._transport)
        self.regions = Regions(self._transport)
        self.settings = Settings(self._transport)
        self.dashboard = Dashboard(self._transport)
        self.analytics = Analytics(self._transport)
        self.audit_log = AuditLog(self._transport)
        self.usage = Usage(self._transport)
        self.channels = Channels(self._transport)
        self.integrations = Integrations(self._transport)
        self.project_integrations = ProjectIntegrations(self._transport)
        self.project_auth = ProjectAuth(self._transport)
        self.external_keys = ExternalKeys(self._transport)
        self.mcp = MCP(self._transport)
        # P3 LLM / model surface
        self.models = Models(self._transport)
        self.completions = Completions(self._transport)
        self.embeddings = Embeddings(self._transport)
        self.provider_defaults = ProviderDefaults(self._transport)
        # P4 platform features
        self.benchmarks = Benchmarks(self._transport)
        self.command_center = CommandCenter(self._transport)
        self.community = Community(self._transport)
        self.email = Email(self._transport)
        self.builder_sessions = BuilderSessions(self._transport)
        self.snapshots = SnapshotsStandalone(self._transport)
        # Egress (security) namespaces — secrets vault, network policy, audit
        self.secrets = EgressSecrets(self._transport)
        self.network = EgressNetwork(self._transport)
        self.audit = EgressAudit(self._transport)

    # -- credits / billing --

    def get_balance(self) -> CreditBalance:
        """Get the current credit balance."""
        data = self._transport.request("GET", "/credits/balance")
        return CreditBalance.model_validate(data)

    def get_transactions(self) -> CreditTransactionList:
        """Get credit transaction history."""
        data = self._transport.request("GET", "/credits/transactions")
        return CreditTransactionList.model_validate(data)

    def get_usage(self) -> CreditUsage:
        """Get current period credit usage."""
        data = self._transport.request("GET", "/credits/usage")
        return CreditUsage.model_validate(data)

    # -- lifecycle --

    def close(self) -> None:
        """Close the underlying HTTP transport."""
        self._transport.close()

    def __enter__(self) -> "Miosa":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"Miosa(base_url={self._transport._base_url!r})"


class AsyncMiosa:
    """Asynchronous MIOSA API client.

    Usage::

        from miosa import AsyncMiosa

        async with AsyncMiosa(api_key="msk_u_...") as client:
            computer = await client.computers.create(name="my-agent")
            await computer.start()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        resolved_key = api_key or os.environ.get("MIOSA_API_KEY")
        if not resolved_key:
            raise ValueError(
                "No API key provided. Pass api_key= or set the MIOSA_API_KEY "
                "environment variable."
            )

        resolved_url = base_url or os.environ.get("MIOSA_BASE_URL", DEFAULT_BASE_URL)

        self._transport = AsyncTransport(
            api_key=resolved_key,
            base_url=resolved_url,
            timeout=timeout,
            max_retries=max_retries,
        )

        self.computers = AsyncComputersResource(self._transport)
        self.sandboxes = AsyncSandboxes(self._transport)
        self.deployments = AsyncDeployments(self._transport)
        self.workspaces = AsyncWorkspaces(self._transport)
        self.admin = AsyncAdmin(self._transport)
        self.open_computers = AsyncOpenComputers(self._transport)
        # P1 data + platform primitives
        self.databases = AsyncDatabases(self._transport)
        self.storage = AsyncStorage(self._transport)
        self.volumes = AsyncVolumes(self._transport)
        self.custom_domains = AsyncFlatCustomDomains(self._transport)
        self.functions = AsyncFunctions(self._transport)
        self.cron_jobs = AsyncCronJobs(self._transport)
        self.health_checks = AsyncHealthChecks(self._transport)
        self.webhooks = AsyncWebhooks(self._transport)
        self.sandbox_templates = AsyncSandboxTemplates(self._transport)
        self.api_keys = AsyncApiKeys(self._transport)
        # P2 tenant + platform admin
        self.tenant = AsyncTenant(self._transport)
        self.regions = AsyncRegions(self._transport)
        self.settings = AsyncSettings(self._transport)
        self.dashboard = AsyncDashboard(self._transport)
        self.analytics = AsyncAnalytics(self._transport)
        self.audit_log = AsyncAuditLog(self._transport)
        self.usage = AsyncUsage(self._transport)
        self.channels = AsyncChannels(self._transport)
        self.integrations = AsyncIntegrations(self._transport)
        self.project_integrations = AsyncProjectIntegrations(self._transport)
        self.project_auth = AsyncProjectAuth(self._transport)
        self.external_keys = AsyncExternalKeys(self._transport)
        self.mcp = AsyncMCP(self._transport)
        # P3 LLM / model surface
        self.models = AsyncModels(self._transport)
        self.completions = AsyncCompletions(self._transport)
        self.embeddings = AsyncEmbeddings(self._transport)
        self.provider_defaults = AsyncProviderDefaults(self._transport)
        # P4 platform features
        self.benchmarks = AsyncBenchmarks(self._transport)
        self.command_center = AsyncCommandCenter(self._transport)
        self.community = AsyncCommunity(self._transport)
        self.email = AsyncEmail(self._transport)
        self.builder_sessions = AsyncBuilderSessions(self._transport)
        self.snapshots = AsyncSnapshotsStandalone(self._transport)
        # Egress (security) namespaces — secrets vault, network policy, audit
        self.secrets = AsyncEgressSecrets(self._transport)
        self.network = AsyncEgressNetwork(self._transport)
        self.audit = AsyncEgressAudit(self._transport)

    async def get_balance(self) -> CreditBalance:
        data = await self._transport.request("GET", "/credits/balance")
        return CreditBalance.model_validate(data)

    async def get_transactions(self) -> CreditTransactionList:
        data = await self._transport.request("GET", "/credits/transactions")
        return CreditTransactionList.model_validate(data)

    async def get_usage(self) -> CreditUsage:
        data = await self._transport.request("GET", "/credits/usage")
        return CreditUsage.model_validate(data)

    async def close(self) -> None:
        await self._transport.close()

    async def __aenter__(self) -> "AsyncMiosa":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    def __repr__(self) -> str:
        return f"AsyncMiosa(base_url={self._transport._base_url!r})"
