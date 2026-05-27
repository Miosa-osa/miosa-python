"""Layer 2 scoped delegation tokens."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


class Tokens:
    """
    Layer 2 scoped delegation tokens.

    White-label customers (e.g. ClinicIQ) authenticate with a master ``msk_*``
    key and mint short-lived JWTs bound to a specific end-user and workspace.
    The resulting token carries only the requested scopes — no privilege
    escalation beyond the caller's own scopes is possible.

    Example::

        import miosa

        client = miosa.Miosa(api_key="msk_u_...")
        result = client.tokens.create_scoped(
            user_id="end-user-123",
            workspace_id="ws_abc...",
            expires_in_seconds=3600,
            scopes=["sandboxes:create", "sandboxes:exec"],
        )
        token = result["token"]       # JWT to embed in the client-side app
        expires_at = result["expires_at"]
        scopes = result["scopes"]
    """

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def create_scoped(
        self,
        *,
        user_id: str,
        workspace_id: str,
        expires_in_seconds: int = 3600,
        scopes: Optional[List[str]] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        """Mint a short-lived scoped delegation token.

        The caller must authenticate with a Layer 1 tenant master key.

        :param user_id: Opaque end-user identifier (string, stored in JWT claims).
        :param workspace_id: UUID of the workspace; must belong to caller's tenant.
        :param expires_in_seconds: Positive integer ≤ 86400. Defaults to 3600 (1 h).
        :param scopes: Subset of the caller's scopes to grant. ``None`` inherits all.
        :returns: Dict with ``token`` (JWT), ``expires_at`` (ISO 8601), ``scopes``.
        :raises ValueError: If ``user_id`` or ``workspace_id`` are empty.
        """
        if not user_id:
            raise ValueError("user_id is required")
        if not workspace_id:
            raise ValueError("workspace_id is required")

        body: Dict[str, Any] = {
            "user_id": user_id,
            "workspace_id": workspace_id,
            "expires_in_seconds": expires_in_seconds,
        }
        if scopes is not None:
            body["scopes"] = scopes
        body.update({k: v for k, v in extra.items() if v is not None})

        return self._t.request("POST", "/tokens/scoped", json=body)


class AsyncTokens:
    """Async variant of :class:`Tokens`."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def create_scoped(
        self,
        *,
        user_id: str,
        workspace_id: str,
        expires_in_seconds: int = 3600,
        scopes: Optional[List[str]] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        """Mint a short-lived scoped delegation token (async)."""
        if not user_id:
            raise ValueError("user_id is required")
        if not workspace_id:
            raise ValueError("workspace_id is required")

        body: Dict[str, Any] = {
            "user_id": user_id,
            "workspace_id": workspace_id,
            "expires_in_seconds": expires_in_seconds,
        }
        if scopes is not None:
            body["scopes"] = scopes
        body.update({k: v for k, v in extra.items() if v is not None})

        return await self._t.request("POST", "/tokens/scoped", json=body)
