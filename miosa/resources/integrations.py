"""Integrations — OAuth account-level connections (GitHub, Slack, Linear, Discord)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(
    data: Any,
    keys: tuple[str, ...] = ("data", "integrations", "catalog", "items"),
) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class Integrations:
    """OAuth integrations — GitHub, Slack, Linear, Discord."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self) -> List[Dict[str, Any]]:
        """List active OAuth integrations for the tenant."""
        data = self._t.request("GET", "/integrations")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def catalog(self) -> List[Dict[str, Any]]:
        """List available providers in the integration catalog."""
        data = self._t.request("GET", "/integrations/catalog")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def start(self, provider: str) -> Dict[str, Any]:
        """Begin the OAuth flow for a provider — returns an authorize URL."""
        return _unwrap(self._t.request("GET", f"/integrations/{provider}/start"))

    def refresh(self, provider: str) -> Dict[str, Any]:
        """Force-refresh the access token for a provider."""
        return _unwrap(
            self._t.request("POST", f"/integrations/{provider}/refresh")
        )

    def disconnect(self, provider: str) -> None:
        """Disconnect (revoke) an integration."""
        self._t.request("DELETE", f"/integrations/{provider}")

    # ── GitHub-specific capabilities ────────────────────────────────────

    def github_repos(self) -> List[Dict[str, Any]]:
        """List GitHub repositories accessible to this integration."""
        data = self._t.request("GET", "/integrations/github/repos")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def github_ssh_keys(self) -> List[Dict[str, Any]]:
        """List configured GitHub deploy keys."""
        data = self._t.request("GET", "/integrations/github/ssh-keys")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    # ── Test hooks ──────────────────────────────────────────────────────

    def slack_send_test(self, **body: Any) -> Dict[str, Any]:
        """Send a test message to the connected Slack channel."""
        json_body = {k: v for k, v in body.items() if v is not None}
        return _unwrap(
            self._t.request(
                "POST", "/integrations/slack/send-test", json_body=json_body
            )
        )

    def discord_send_test(self, **body: Any) -> Dict[str, Any]:
        """Send a test message to the connected Discord channel."""
        json_body = {k: v for k, v in body.items() if v is not None}
        return _unwrap(
            self._t.request(
                "POST", "/integrations/discord/send-test", json_body=json_body
            )
        )

    # ── Linear dedicated controller ────────────────────────────────────

    def linear_start(self) -> Dict[str, Any]:
        """Begin Linear OAuth — Linear has provider-specific error shapes."""
        return _unwrap(self._t.request("GET", "/integrations/linear/start"))

    def linear_create_issue(self, **body: Any) -> Dict[str, Any]:
        """Create a Linear issue via the connected workspace."""
        json_body = {k: v for k, v in body.items() if v is not None}
        return _unwrap(
            self._t.request(
                "POST", "/integrations/linear/create-issue", json_body=json_body
            )
        )


class AsyncIntegrations:
    """Async OAuth integrations."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", "/integrations")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def catalog(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", "/integrations/catalog")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def start(self, provider: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request("GET", f"/integrations/{provider}/start")
        )

    async def refresh(self, provider: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request("POST", f"/integrations/{provider}/refresh")
        )

    async def disconnect(self, provider: str) -> None:
        await self._t.request("DELETE", f"/integrations/{provider}")

    async def github_repos(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", "/integrations/github/repos")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def github_ssh_keys(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", "/integrations/github/ssh-keys")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def slack_send_test(self, **body: Any) -> Dict[str, Any]:
        json_body = {k: v for k, v in body.items() if v is not None}
        return _unwrap(
            await self._t.request(
                "POST", "/integrations/slack/send-test", json_body=json_body
            )
        )

    async def discord_send_test(self, **body: Any) -> Dict[str, Any]:
        json_body = {k: v for k, v in body.items() if v is not None}
        return _unwrap(
            await self._t.request(
                "POST", "/integrations/discord/send-test", json_body=json_body
            )
        )

    async def linear_start(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", "/integrations/linear/start"))

    async def linear_create_issue(self, **body: Any) -> Dict[str, Any]:
        json_body = {k: v for k, v in body.items() if v is not None}
        return _unwrap(
            await self._t.request(
                "POST", "/integrations/linear/create-issue", json_body=json_body
            )
        )
