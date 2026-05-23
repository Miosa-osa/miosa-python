"""Egress secrets — encrypted API key + OAuth credential vault.

Backed by ``/api/v1/egress/secrets`` (and ``/egress/bindings``,
``/egress/oauth/*``). Three access surfaces are provided:

* :class:`EgressSecrets` — tenant-wide CRUD + OAuth connect.
* :class:`SandboxSecrets` — bound to a sandbox; pre-scopes
  ``resource_id`` + ``resource_type="sandbox"`` for bindings and listing.
* :class:`ComputerSecrets` — bound to a computer; pre-scopes
  ``resource_id`` + ``resource_type="computer"``.

The ``connect()`` method returns an :class:`OauthFlow` object exposing
``authorize_url`` and ``wait_for_completion(timeout=...)``. The SDK
does *not* open a browser — the caller is responsible for surfacing
``authorize_url`` to the end user.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


_SECRET_PATH = "/egress/secrets"
_BINDING_PATH = "/egress/bindings"
_OAUTH_PROVIDERS_PATH = "/egress/oauth/providers"
_OAUTH_START_PATH = "/egress/oauth/start"
_OAUTH_STATUS_PATH = "/egress/oauth/status"


def _unwrap(data: Any, keys: tuple[str, ...] = ("data", "secret", "binding", "items")) -> Any:
    if isinstance(data, dict):
        for key in keys:
            if key in data and len(data) <= 2:
                return data[key]
    return data


def _unwrap_list(data: Any, keys: tuple[str, ...] = ("data", "secrets", "bindings", "items")) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return cast(List[Dict[str, Any]], data)
    if isinstance(data, dict):
        for key in keys:
            items = data.get(key)
            if isinstance(items, list):
                return cast(List[Dict[str, Any]], items)
    return []


def _strip_none(body: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in body.items() if v is not None}


# ---------------------------------------------------------------------------
# OAuth flow handle
# ---------------------------------------------------------------------------


@dataclass
class OauthFlow:
    """A pending OAuth flow.

    Attributes:
        authorize_url: URL the end user must visit to grant consent.
        state: Opaque server-issued token identifying this flow.
        provider: Provider name (e.g. ``"github"``, ``"slack"``).
        data: Raw response payload from ``POST /egress/oauth/start``.
    """

    authorize_url: str
    state: str
    provider: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    _transport: Any = field(repr=False, compare=False, default=None)

    def wait_for_completion(self, timeout: float = 300.0, poll_interval: float = 2.0) -> Dict[str, Any]:
        """Poll ``GET /egress/oauth/status?state=...`` until the OAuth flow completes.

        Returns the status payload once the upstream provider issues
        tokens (the body will typically contain a ``secret_id`` and
        ``status: "completed"``).

        Raises :class:`TimeoutError` if the flow does not complete
        within *timeout* seconds.
        """
        if self._transport is None:  # pragma: no cover — only when constructed by hand
            raise RuntimeError("OauthFlow has no transport bound")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            data = self._transport.request(
                "GET", _OAUTH_STATUS_PATH, params={"state": self.state}
            )
            payload = _unwrap(data) if isinstance(data, dict) else data
            if isinstance(payload, dict):
                status = payload.get("status")
                if status in {"completed", "ready", "succeeded"}:
                    return payload
                if status in {"failed", "error", "denied"}:
                    raise RuntimeError(
                        f"OAuth flow {self.state} ended in status={status!r}: "
                        f"{payload.get('error') or payload.get('message') or 'no detail'}"
                    )
            time.sleep(poll_interval)
        raise TimeoutError(f"OAuth flow {self.state} did not complete within {timeout}s")


@dataclass
class AsyncOauthFlow:
    """Async counterpart of :class:`OauthFlow`."""

    authorize_url: str
    state: str
    provider: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    _transport: Any = field(repr=False, compare=False, default=None)

    async def wait_for_completion(self, timeout: float = 300.0, poll_interval: float = 2.0) -> Dict[str, Any]:
        if self._transport is None:  # pragma: no cover
            raise RuntimeError("AsyncOauthFlow has no transport bound")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            data = await self._transport.request(
                "GET", _OAUTH_STATUS_PATH, params={"state": self.state}
            )
            payload = _unwrap(data) if isinstance(data, dict) else data
            if isinstance(payload, dict):
                status = payload.get("status")
                if status in {"completed", "ready", "succeeded"}:
                    return payload
                if status in {"failed", "error", "denied"}:
                    raise RuntimeError(
                        f"OAuth flow {self.state} ended in status={status!r}: "
                        f"{payload.get('error') or payload.get('message') or 'no detail'}"
                    )
            await asyncio.sleep(poll_interval)
        raise TimeoutError(f"OAuth flow {self.state} did not complete within {timeout}s")


# ---------------------------------------------------------------------------
# Shared body helpers
# ---------------------------------------------------------------------------


def _build_set_body(
    name: str,
    value: str,
    *,
    type: str = "api_key",
    scope: str = "user",
    expose_as_env: Optional[str],
    workspace_id: Optional[str],
    owner_user_id: Optional[str],
    external_user_id: Optional[str],
    external_workspace_id: Optional[str],
    resource_id: Optional[str],
    resource_type: Optional[str],
    refresh_token: Optional[str],
    expires_at: Optional[str],
    metadata: Optional[Dict[str, Any]],
    extra: Dict[str, Any],
) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "name": name,
        "value": value,
        "type": type,
        "scope": scope,
    }
    optional = {
        "expose_as_env": expose_as_env,
        "workspace_id": workspace_id,
        "owner_user_id": owner_user_id,
        "external_user_id": external_user_id,
        "external_workspace_id": external_workspace_id,
        "resource_id": resource_id,
        "resource_type": resource_type,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
        "metadata": metadata,
    }
    body.update(_strip_none(optional))
    body.update({k: v for k, v in extra.items() if v is not None})
    return body


def _build_oauth_start_body(
    provider: str,
    *,
    expose_as_env: Optional[str],
    scope: Optional[str],
    owner_user_id: Optional[str],
    external_user_id: Optional[str],
    external_workspace_id: Optional[str],
    resource_id: Optional[str],
    resource_type: Optional[str],
    redirect_uri: Optional[str],
    extra: Dict[str, Any],
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"provider": provider}
    optional = {
        "expose_as_env": expose_as_env,
        "scope": scope,
        "owner_user_id": owner_user_id,
        "external_user_id": external_user_id,
        "external_workspace_id": external_workspace_id,
        "resource_id": resource_id,
        "resource_type": resource_type,
        "redirect_uri": redirect_uri,
    }
    body.update(_strip_none(optional))
    body.update({k: v for k, v in extra.items() if v is not None})
    return body


# ---------------------------------------------------------------------------
# Sync — tenant-wide
# ---------------------------------------------------------------------------


class EgressSecrets:
    """Tenant-wide secret + OAuth credential management."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    # -- secrets --

    def set(
        self,
        *,
        name: str,
        value: str,
        type: str = "api_key",
        scope: str = "user",
        expose_as_env: Optional[str] = None,
        workspace_id: Optional[str] = None,
        owner_user_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_workspace_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        refresh_token: Optional[str] = None,
        expires_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create a secret. When ``expose_as_env`` and ``resource_id`` are
        both provided the backend also creates a binding so the value is
        injected as an env-var in that resource.
        """
        body = _build_set_body(
            name,
            value,
            type=type,
            scope=scope,
            expose_as_env=expose_as_env,
            workspace_id=workspace_id,
            owner_user_id=owner_user_id,
            external_user_id=external_user_id,
            external_workspace_id=external_workspace_id,
            resource_id=resource_id,
            resource_type=resource_type,
            refresh_token=refresh_token,
            expires_at=expires_at,
            metadata=metadata,
            extra=kwargs,
        )
        data = self._t.request("POST", _SECRET_PATH, json_body=body)
        return cast(Dict[str, Any], _unwrap(data))

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        """List secrets. Filters: ``scope``, ``workspace_id``,
        ``owner_user_id``, ``external_user_id``, ``external_workspace_id``,
        ``resource_id``, ``resource_type``, ``type``.
        """
        params = _strip_none(filters)
        data = self._t.request("GET", _SECRET_PATH, params=params or None)
        return _unwrap_list(data)

    def get(self, secret_id: str) -> Dict[str, Any]:
        data = self._t.request("GET", f"{_SECRET_PATH}/{secret_id}")
        return cast(Dict[str, Any], _unwrap(data))

    def rotate(
        self,
        secret_id: str,
        new_value: str,
        *,
        refresh_token: Optional[str] = None,
        expires_at: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Rotate the secret's value (``PATCH /egress/secrets/:id``)."""
        body: Dict[str, Any] = {"value": new_value}
        if refresh_token is not None:
            body["refresh_token"] = refresh_token
        if expires_at is not None:
            body["expires_at"] = expires_at
        body.update({k: v for k, v in kwargs.items() if v is not None})
        data = self._t.request("PATCH", f"{_SECRET_PATH}/{secret_id}", json_body=body)
        return cast(Dict[str, Any], _unwrap(data))

    def delete(self, secret_id: str) -> None:
        self._t.request("DELETE", f"{_SECRET_PATH}/{secret_id}")

    # -- bindings --

    def create_binding(
        self,
        *,
        secret_id: str,
        resource_id: str,
        resource_type: str,
        expose_as_env: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "secret_id": secret_id,
            "resource_id": resource_id,
            "resource_type": resource_type,
            "expose_as_env": expose_as_env,
        }
        body.update({k: v for k, v in kwargs.items() if v is not None})
        data = self._t.request("POST", _BINDING_PATH, json_body=body)
        return cast(Dict[str, Any], _unwrap(data))

    def list_bindings(
        self,
        *,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        secret_id: Optional[str] = None,
        **filters: Any,
    ) -> List[Dict[str, Any]]:
        params = _strip_none({
            "resource_id": resource_id,
            "resource_type": resource_type,
            "secret_id": secret_id,
            **filters,
        })
        data = self._t.request("GET", _BINDING_PATH, params=params or None)
        return _unwrap_list(data)

    def delete_binding(self, binding_id: str) -> None:
        self._t.request("DELETE", f"{_BINDING_PATH}/{binding_id}")

    # -- oauth --

    def providers(self) -> List[Dict[str, Any]]:
        """List OAuth providers visible to the current tenant."""
        data = self._t.request("GET", _OAUTH_PROVIDERS_PATH)
        return _unwrap_list(data, keys=("data", "providers", "items"))

    def connect(
        self,
        provider: str,
        *,
        expose_as_env: Optional[str] = None,
        scope: Optional[str] = None,
        owner_user_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_workspace_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        **kwargs: Any,
    ) -> OauthFlow:
        """Start an OAuth Connect flow.

        Returns an :class:`OauthFlow` object — the caller is responsible
        for opening ``flow.authorize_url`` in the end user's browser and
        then calling :meth:`OauthFlow.wait_for_completion` (or polling
        themselves) to receive the resulting secret id.
        """
        body = _build_oauth_start_body(
            provider,
            expose_as_env=expose_as_env,
            scope=scope,
            owner_user_id=owner_user_id,
            external_user_id=external_user_id,
            external_workspace_id=external_workspace_id,
            resource_id=resource_id,
            resource_type=resource_type,
            redirect_uri=redirect_uri,
            extra=kwargs,
        )
        data = self._t.request("POST", _OAUTH_START_PATH, json_body=body)
        payload = cast(Dict[str, Any], _unwrap(data) if isinstance(data, dict) else {})
        return OauthFlow(
            authorize_url=str(payload.get("authorize_url") or payload.get("authorizeUrl") or ""),
            state=str(payload.get("state") or ""),
            provider=provider,
            data=payload,
            _transport=self._t,
        )


# ---------------------------------------------------------------------------
# Async — tenant-wide
# ---------------------------------------------------------------------------


class AsyncEgressSecrets:
    """Asynchronous tenant-wide secret + OAuth credential management."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def set(
        self,
        *,
        name: str,
        value: str,
        type: str = "api_key",
        scope: str = "user",
        expose_as_env: Optional[str] = None,
        workspace_id: Optional[str] = None,
        owner_user_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_workspace_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        refresh_token: Optional[str] = None,
        expires_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        body = _build_set_body(
            name,
            value,
            type=type,
            scope=scope,
            expose_as_env=expose_as_env,
            workspace_id=workspace_id,
            owner_user_id=owner_user_id,
            external_user_id=external_user_id,
            external_workspace_id=external_workspace_id,
            resource_id=resource_id,
            resource_type=resource_type,
            refresh_token=refresh_token,
            expires_at=expires_at,
            metadata=metadata,
            extra=kwargs,
        )
        data = await self._t.request("POST", _SECRET_PATH, json_body=body)
        return cast(Dict[str, Any], _unwrap(data))

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = _strip_none(filters)
        data = await self._t.request("GET", _SECRET_PATH, params=params or None)
        return _unwrap_list(data)

    async def get(self, secret_id: str) -> Dict[str, Any]:
        data = await self._t.request("GET", f"{_SECRET_PATH}/{secret_id}")
        return cast(Dict[str, Any], _unwrap(data))

    async def rotate(
        self,
        secret_id: str,
        new_value: str,
        *,
        refresh_token: Optional[str] = None,
        expires_at: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"value": new_value}
        if refresh_token is not None:
            body["refresh_token"] = refresh_token
        if expires_at is not None:
            body["expires_at"] = expires_at
        body.update({k: v for k, v in kwargs.items() if v is not None})
        data = await self._t.request("PATCH", f"{_SECRET_PATH}/{secret_id}", json_body=body)
        return cast(Dict[str, Any], _unwrap(data))

    async def delete(self, secret_id: str) -> None:
        await self._t.request("DELETE", f"{_SECRET_PATH}/{secret_id}")

    async def create_binding(
        self,
        *,
        secret_id: str,
        resource_id: str,
        resource_type: str,
        expose_as_env: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "secret_id": secret_id,
            "resource_id": resource_id,
            "resource_type": resource_type,
            "expose_as_env": expose_as_env,
        }
        body.update({k: v for k, v in kwargs.items() if v is not None})
        data = await self._t.request("POST", _BINDING_PATH, json_body=body)
        return cast(Dict[str, Any], _unwrap(data))

    async def list_bindings(
        self,
        *,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        secret_id: Optional[str] = None,
        **filters: Any,
    ) -> List[Dict[str, Any]]:
        params = _strip_none({
            "resource_id": resource_id,
            "resource_type": resource_type,
            "secret_id": secret_id,
            **filters,
        })
        data = await self._t.request("GET", _BINDING_PATH, params=params or None)
        return _unwrap_list(data)

    async def delete_binding(self, binding_id: str) -> None:
        await self._t.request("DELETE", f"{_BINDING_PATH}/{binding_id}")

    async def providers(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", _OAUTH_PROVIDERS_PATH)
        return _unwrap_list(data, keys=("data", "providers", "items"))

    async def connect(
        self,
        provider: str,
        *,
        expose_as_env: Optional[str] = None,
        scope: Optional[str] = None,
        owner_user_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_workspace_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncOauthFlow:
        body = _build_oauth_start_body(
            provider,
            expose_as_env=expose_as_env,
            scope=scope,
            owner_user_id=owner_user_id,
            external_user_id=external_user_id,
            external_workspace_id=external_workspace_id,
            resource_id=resource_id,
            resource_type=resource_type,
            redirect_uri=redirect_uri,
            extra=kwargs,
        )
        data = await self._t.request("POST", _OAUTH_START_PATH, json_body=body)
        payload = cast(Dict[str, Any], _unwrap(data) if isinstance(data, dict) else {})
        return AsyncOauthFlow(
            authorize_url=str(payload.get("authorize_url") or payload.get("authorizeUrl") or ""),
            state=str(payload.get("state") or ""),
            provider=provider,
            data=payload,
            _transport=self._t,
        )


# ---------------------------------------------------------------------------
# Bound — resource-scoped wrappers
# ---------------------------------------------------------------------------


class _BoundSecretsBase:
    """Shared init for bound (sandbox / computer) secret namespaces."""

    _resource_type: str = ""

    def __init__(self, transport: Any, resource_id: str) -> None:
        self._t = transport
        self._resource_id = resource_id


class SandboxSecrets(_BoundSecretsBase):
    """Sandbox-bound view of :class:`EgressSecrets`.

    Calls pre-scope ``resource_id`` and ``resource_type="sandbox"``.
    """

    _resource_type = "sandbox"

    def __init__(self, transport: SyncTransport, resource_id: str) -> None:
        super().__init__(transport, resource_id)
        self._delegate = EgressSecrets(transport)

    def set(self, *, name: str, value: str, **kwargs: Any) -> Dict[str, Any]:
        kwargs.setdefault("resource_id", self._resource_id)
        kwargs.setdefault("resource_type", self._resource_type)
        return self._delegate.set(name=name, value=value, **kwargs)

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        filters.setdefault("resource_id", self._resource_id)
        filters.setdefault("resource_type", self._resource_type)
        return self._delegate.list(**filters)

    def get(self, secret_id: str) -> Dict[str, Any]:
        return self._delegate.get(secret_id)

    def rotate(self, secret_id: str, new_value: str, **kwargs: Any) -> Dict[str, Any]:
        return self._delegate.rotate(secret_id, new_value, **kwargs)

    def delete(self, secret_id: str) -> None:
        self._delegate.delete(secret_id)

    def connect(self, provider: str, **kwargs: Any) -> OauthFlow:
        kwargs.setdefault("resource_id", self._resource_id)
        kwargs.setdefault("resource_type", self._resource_type)
        return self._delegate.connect(provider, **kwargs)

    def list_bindings(self, **filters: Any) -> List[Dict[str, Any]]:
        filters.setdefault("resource_id", self._resource_id)
        filters.setdefault("resource_type", self._resource_type)
        return self._delegate.list_bindings(**filters)


class AsyncSandboxSecrets(_BoundSecretsBase):
    """Async sandbox-bound secrets namespace."""

    _resource_type = "sandbox"

    def __init__(self, transport: AsyncTransport, resource_id: str) -> None:
        super().__init__(transport, resource_id)
        self._delegate = AsyncEgressSecrets(transport)

    async def set(self, *, name: str, value: str, **kwargs: Any) -> Dict[str, Any]:
        kwargs.setdefault("resource_id", self._resource_id)
        kwargs.setdefault("resource_type", self._resource_type)
        return await self._delegate.set(name=name, value=value, **kwargs)

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        filters.setdefault("resource_id", self._resource_id)
        filters.setdefault("resource_type", self._resource_type)
        return await self._delegate.list(**filters)

    async def get(self, secret_id: str) -> Dict[str, Any]:
        return await self._delegate.get(secret_id)

    async def rotate(self, secret_id: str, new_value: str, **kwargs: Any) -> Dict[str, Any]:
        return await self._delegate.rotate(secret_id, new_value, **kwargs)

    async def delete(self, secret_id: str) -> None:
        await self._delegate.delete(secret_id)

    async def connect(self, provider: str, **kwargs: Any) -> AsyncOauthFlow:
        kwargs.setdefault("resource_id", self._resource_id)
        kwargs.setdefault("resource_type", self._resource_type)
        return await self._delegate.connect(provider, **kwargs)

    async def list_bindings(self, **filters: Any) -> List[Dict[str, Any]]:
        filters.setdefault("resource_id", self._resource_id)
        filters.setdefault("resource_type", self._resource_type)
        return await self._delegate.list_bindings(**filters)


class ComputerSecrets(SandboxSecrets):
    """Computer-bound secrets — same shape, ``resource_type='computer'``."""

    _resource_type = "computer"


class AsyncComputerSecrets(AsyncSandboxSecrets):
    """Async computer-bound secrets."""

    _resource_type = "computer"


__all__ = [
    "AsyncComputerSecrets",
    "AsyncEgressSecrets",
    "AsyncOauthFlow",
    "AsyncSandboxSecrets",
    "ComputerSecrets",
    "EgressSecrets",
    "OauthFlow",
    "SandboxSecrets",
]
