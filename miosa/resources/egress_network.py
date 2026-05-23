"""Egress network — policies, allowlist, suggestions.

Backed by ``/api/v1/egress/policies``, ``/api/v1/egress/allowlist``, and
``/api/v1/egress/audit/suggestions``.

The egress firewall layers on top of the per-resource ``NetworkPolicy``
(which is the legacy nftables resource). The egress namespace adds:

* multi-rule **policies** that can be attached to resources,
* an **allowlist** (host + method + path-glob) that the proxy enforces,
* a **mode** flag (``audit_only`` vs ``enforce``) so callers can run in
  observe-mode first and graduate to lockdown.
* AI-generated **suggestions** based on recent denied traffic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


_POLICY_PATH = "/egress/policies"
_ALLOWLIST_PATH = "/egress/allowlist"
_SUGGESTIONS_PATH = "/egress/audit/suggestions"


def _unwrap(data: Any, keys: tuple[str, ...] = ("data", "policy", "rule", "items")) -> Any:
    if isinstance(data, dict):
        for key in keys:
            if key in data and len(data) <= 2:
                return data[key]
    return data


def _unwrap_list(data: Any, keys: tuple[str, ...] = ("data", "policies", "rules", "allowlist", "suggestions", "items")) -> List[Dict[str, Any]]:
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


def _build_allow_body(
    host: str,
    *,
    methods: Optional[List[str]],
    path_glob: Optional[str],
    policy_id: Optional[str],
    resource_id: Optional[str],
    resource_type: Optional[str],
    effect: str,
    note: Optional[str],
    extra: Dict[str, Any],
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"host": host, "effect": effect}
    optional = {
        "methods": methods,
        "path_glob": path_glob,
        "policy_id": policy_id,
        "resource_id": resource_id,
        "resource_type": resource_type,
        "note": note,
    }
    body.update(_strip_none(optional))
    body.update({k: v for k, v in extra.items() if v is not None})
    return body


# ---------------------------------------------------------------------------
# Sync — tenant-wide
# ---------------------------------------------------------------------------


class EgressNetwork:
    """Tenant-wide egress allowlist + policy management."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    # -- allowlist --

    def allow(
        self,
        host: str,
        *,
        methods: Optional[List[str]] = None,
        path_glob: Optional[str] = None,
        policy_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        note: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Add an ``allow`` rule for *host* to the allowlist."""
        body = _build_allow_body(
            host,
            methods=methods,
            path_glob=path_glob,
            policy_id=policy_id,
            resource_id=resource_id,
            resource_type=resource_type,
            effect="allow",
            note=note,
            extra=kwargs,
        )
        data = self._t.request("POST", _ALLOWLIST_PATH, json_body=body)
        return cast(Dict[str, Any], _unwrap(data))

    def deny(
        self,
        host: str,
        *,
        methods: Optional[List[str]] = None,
        path_glob: Optional[str] = None,
        policy_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        note: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Add a ``deny`` rule for *host* to the allowlist."""
        body = _build_allow_body(
            host,
            methods=methods,
            path_glob=path_glob,
            policy_id=policy_id,
            resource_id=resource_id,
            resource_type=resource_type,
            effect="deny",
            note=note,
            extra=kwargs,
        )
        data = self._t.request("POST", _ALLOWLIST_PATH, json_body=body)
        return cast(Dict[str, Any], _unwrap(data))

    def rules(
        self,
        *,
        policy_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        **filters: Any,
    ) -> List[Dict[str, Any]]:
        """List allowlist rules. Filter by ``policy_id``, ``resource_id``,
        ``resource_type``.
        """
        params = _strip_none({
            "policy_id": policy_id,
            "resource_id": resource_id,
            "resource_type": resource_type,
            **filters,
        })
        data = self._t.request("GET", _ALLOWLIST_PATH, params=params or None)
        return _unwrap_list(data)

    def remove_rule(self, rule_id: str) -> None:
        """Delete an allowlist rule by id."""
        self._t.request("DELETE", f"{_ALLOWLIST_PATH}/{rule_id}")

    # -- policies --

    def policies(self, **filters: Any) -> List[Dict[str, Any]]:
        """List egress policies."""
        params = _strip_none(filters)
        data = self._t.request("GET", _POLICY_PATH, params=params or None)
        return _unwrap_list(data)

    def create_policy(
        self,
        *,
        name: str,
        mode: str = "enforce",
        default_effect: str = "deny",
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "name": name,
            "mode": mode,
            "default_effect": default_effect,
        }
        body.update(_strip_none({
            "resource_id": resource_id,
            "resource_type": resource_type,
            "description": description,
        }))
        body.update({k: v for k, v in kwargs.items() if v is not None})
        data = self._t.request("POST", _POLICY_PATH, json_body=body)
        return cast(Dict[str, Any], _unwrap(data))

    def update_policy(
        self,
        policy_id: str,
        *,
        mode: Optional[str] = None,
        default_effect: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        body = _strip_none({
            "mode": mode,
            "default_effect": default_effect,
            "name": name,
            "description": description,
        })
        body.update({k: v for k, v in kwargs.items() if v is not None})
        data = self._t.request("PATCH", f"{_POLICY_PATH}/{policy_id}", json_body=body)
        return cast(Dict[str, Any], _unwrap(data))

    # -- mode helpers --

    def lockdown(
        self,
        *,
        policy_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Set the policy to ``mode=enforce`` — denied requests are blocked."""
        return self._set_mode(
            mode="enforce",
            policy_id=policy_id,
            resource_id=resource_id,
            resource_type=resource_type,
        )

    def observe(
        self,
        *,
        policy_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Set the policy to ``mode=audit_only`` — log but do not block."""
        return self._set_mode(
            mode="audit_only",
            policy_id=policy_id,
            resource_id=resource_id,
            resource_type=resource_type,
        )

    def _set_mode(
        self,
        *,
        mode: str,
        policy_id: Optional[str],
        resource_id: Optional[str],
        resource_type: Optional[str],
    ) -> Dict[str, Any]:
        if policy_id is None and (resource_id is None or resource_type is None):
            # No policy id and no resource scope — patch the tenant-default
            # policy. Backend routes ``PATCH /egress/policies`` (no id) as
            # update-default.
            data = self._t.request("PATCH", _POLICY_PATH, json_body={"mode": mode})
            return cast(Dict[str, Any], _unwrap(data))
        if policy_id is not None:
            return self.update_policy(policy_id, mode=mode)
        body = _strip_none({
            "mode": mode,
            "resource_id": resource_id,
            "resource_type": resource_type,
        })
        data = self._t.request("PATCH", _POLICY_PATH, json_body=body)
        return cast(Dict[str, Any], _unwrap(data))

    # -- suggestions --

    def suggestions(
        self,
        *,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        since: str = "7d",
        **filters: Any,
    ) -> List[Dict[str, Any]]:
        """Return AI-generated allowlist suggestions from recent denied egress."""
        params = _strip_none({
            "resource_id": resource_id,
            "resource_type": resource_type,
            "since": since,
            **filters,
        })
        data = self._t.request("GET", _SUGGESTIONS_PATH, params=params or None)
        return _unwrap_list(data)


# ---------------------------------------------------------------------------
# Async — tenant-wide
# ---------------------------------------------------------------------------


class AsyncEgressNetwork:
    """Asynchronous tenant-wide egress allowlist + policy management."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def allow(
        self,
        host: str,
        *,
        methods: Optional[List[str]] = None,
        path_glob: Optional[str] = None,
        policy_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        note: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        body = _build_allow_body(
            host,
            methods=methods,
            path_glob=path_glob,
            policy_id=policy_id,
            resource_id=resource_id,
            resource_type=resource_type,
            effect="allow",
            note=note,
            extra=kwargs,
        )
        data = await self._t.request("POST", _ALLOWLIST_PATH, json_body=body)
        return cast(Dict[str, Any], _unwrap(data))

    async def deny(
        self,
        host: str,
        *,
        methods: Optional[List[str]] = None,
        path_glob: Optional[str] = None,
        policy_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        note: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        body = _build_allow_body(
            host,
            methods=methods,
            path_glob=path_glob,
            policy_id=policy_id,
            resource_id=resource_id,
            resource_type=resource_type,
            effect="deny",
            note=note,
            extra=kwargs,
        )
        data = await self._t.request("POST", _ALLOWLIST_PATH, json_body=body)
        return cast(Dict[str, Any], _unwrap(data))

    async def rules(
        self,
        *,
        policy_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        **filters: Any,
    ) -> List[Dict[str, Any]]:
        params = _strip_none({
            "policy_id": policy_id,
            "resource_id": resource_id,
            "resource_type": resource_type,
            **filters,
        })
        data = await self._t.request("GET", _ALLOWLIST_PATH, params=params or None)
        return _unwrap_list(data)

    async def remove_rule(self, rule_id: str) -> None:
        await self._t.request("DELETE", f"{_ALLOWLIST_PATH}/{rule_id}")

    async def policies(self, **filters: Any) -> List[Dict[str, Any]]:
        params = _strip_none(filters)
        data = await self._t.request("GET", _POLICY_PATH, params=params or None)
        return _unwrap_list(data)

    async def create_policy(
        self,
        *,
        name: str,
        mode: str = "enforce",
        default_effect: str = "deny",
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "name": name,
            "mode": mode,
            "default_effect": default_effect,
        }
        body.update(_strip_none({
            "resource_id": resource_id,
            "resource_type": resource_type,
            "description": description,
        }))
        body.update({k: v for k, v in kwargs.items() if v is not None})
        data = await self._t.request("POST", _POLICY_PATH, json_body=body)
        return cast(Dict[str, Any], _unwrap(data))

    async def update_policy(
        self,
        policy_id: str,
        *,
        mode: Optional[str] = None,
        default_effect: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        body = _strip_none({
            "mode": mode,
            "default_effect": default_effect,
            "name": name,
            "description": description,
        })
        body.update({k: v for k, v in kwargs.items() if v is not None})
        data = await self._t.request("PATCH", f"{_POLICY_PATH}/{policy_id}", json_body=body)
        return cast(Dict[str, Any], _unwrap(data))

    async def lockdown(
        self,
        *,
        policy_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._set_mode(
            mode="enforce",
            policy_id=policy_id,
            resource_id=resource_id,
            resource_type=resource_type,
        )

    async def observe(
        self,
        *,
        policy_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._set_mode(
            mode="audit_only",
            policy_id=policy_id,
            resource_id=resource_id,
            resource_type=resource_type,
        )

    async def _set_mode(
        self,
        *,
        mode: str,
        policy_id: Optional[str],
        resource_id: Optional[str],
        resource_type: Optional[str],
    ) -> Dict[str, Any]:
        if policy_id is None and (resource_id is None or resource_type is None):
            data = await self._t.request("PATCH", _POLICY_PATH, json_body={"mode": mode})
            return cast(Dict[str, Any], _unwrap(data))
        if policy_id is not None:
            return await self.update_policy(policy_id, mode=mode)
        body = _strip_none({
            "mode": mode,
            "resource_id": resource_id,
            "resource_type": resource_type,
        })
        data = await self._t.request("PATCH", _POLICY_PATH, json_body=body)
        return cast(Dict[str, Any], _unwrap(data))

    async def suggestions(
        self,
        *,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        since: str = "7d",
        **filters: Any,
    ) -> List[Dict[str, Any]]:
        params = _strip_none({
            "resource_id": resource_id,
            "resource_type": resource_type,
            "since": since,
            **filters,
        })
        data = await self._t.request("GET", _SUGGESTIONS_PATH, params=params or None)
        return _unwrap_list(data)


# ---------------------------------------------------------------------------
# Bound — resource-scoped wrappers
# ---------------------------------------------------------------------------


class SandboxNetwork:
    """Sandbox-bound view of :class:`EgressNetwork`.

    Pre-scopes ``resource_id`` + ``resource_type="sandbox"`` on every
    call.
    """

    _resource_type: str = "sandbox"

    def __init__(self, transport: SyncTransport, resource_id: str) -> None:
        self._t = transport
        self._resource_id = resource_id
        self._delegate = EgressNetwork(transport)

    def allow(self, host: str, **kwargs: Any) -> Dict[str, Any]:
        kwargs.setdefault("resource_id", self._resource_id)
        kwargs.setdefault("resource_type", self._resource_type)
        return self._delegate.allow(host, **kwargs)

    def deny(self, host: str, **kwargs: Any) -> Dict[str, Any]:
        kwargs.setdefault("resource_id", self._resource_id)
        kwargs.setdefault("resource_type", self._resource_type)
        return self._delegate.deny(host, **kwargs)

    def rules(self, **filters: Any) -> List[Dict[str, Any]]:
        filters.setdefault("resource_id", self._resource_id)
        filters.setdefault("resource_type", self._resource_type)
        return self._delegate.rules(**filters)

    def remove_rule(self, rule_id: str) -> None:
        self._delegate.remove_rule(rule_id)

    def lockdown(self, *, policy_id: Optional[str] = None) -> Dict[str, Any]:
        return self._delegate.lockdown(
            policy_id=policy_id,
            resource_id=self._resource_id,
            resource_type=self._resource_type,
        )

    def observe(self, *, policy_id: Optional[str] = None) -> Dict[str, Any]:
        return self._delegate.observe(
            policy_id=policy_id,
            resource_id=self._resource_id,
            resource_type=self._resource_type,
        )

    def suggestions(self, *, since: str = "7d", **filters: Any) -> List[Dict[str, Any]]:
        filters.setdefault("resource_id", self._resource_id)
        filters.setdefault("resource_type", self._resource_type)
        return self._delegate.suggestions(since=since, **filters)

    def policies(self, **filters: Any) -> List[Dict[str, Any]]:
        filters.setdefault("resource_id", self._resource_id)
        filters.setdefault("resource_type", self._resource_type)
        return self._delegate.policies(**filters)


class AsyncSandboxNetwork:
    """Async sandbox-bound network namespace."""

    _resource_type: str = "sandbox"

    def __init__(self, transport: AsyncTransport, resource_id: str) -> None:
        self._t = transport
        self._resource_id = resource_id
        self._delegate = AsyncEgressNetwork(transport)

    async def allow(self, host: str, **kwargs: Any) -> Dict[str, Any]:
        kwargs.setdefault("resource_id", self._resource_id)
        kwargs.setdefault("resource_type", self._resource_type)
        return await self._delegate.allow(host, **kwargs)

    async def deny(self, host: str, **kwargs: Any) -> Dict[str, Any]:
        kwargs.setdefault("resource_id", self._resource_id)
        kwargs.setdefault("resource_type", self._resource_type)
        return await self._delegate.deny(host, **kwargs)

    async def rules(self, **filters: Any) -> List[Dict[str, Any]]:
        filters.setdefault("resource_id", self._resource_id)
        filters.setdefault("resource_type", self._resource_type)
        return await self._delegate.rules(**filters)

    async def remove_rule(self, rule_id: str) -> None:
        await self._delegate.remove_rule(rule_id)

    async def lockdown(self, *, policy_id: Optional[str] = None) -> Dict[str, Any]:
        return await self._delegate.lockdown(
            policy_id=policy_id,
            resource_id=self._resource_id,
            resource_type=self._resource_type,
        )

    async def observe(self, *, policy_id: Optional[str] = None) -> Dict[str, Any]:
        return await self._delegate.observe(
            policy_id=policy_id,
            resource_id=self._resource_id,
            resource_type=self._resource_type,
        )

    async def suggestions(self, *, since: str = "7d", **filters: Any) -> List[Dict[str, Any]]:
        filters.setdefault("resource_id", self._resource_id)
        filters.setdefault("resource_type", self._resource_type)
        return await self._delegate.suggestions(since=since, **filters)

    async def policies(self, **filters: Any) -> List[Dict[str, Any]]:
        filters.setdefault("resource_id", self._resource_id)
        filters.setdefault("resource_type", self._resource_type)
        return await self._delegate.policies(**filters)


class ComputerNetwork(SandboxNetwork):
    """Computer-bound network — same surface, ``resource_type='computer'``."""

    _resource_type = "computer"


class AsyncComputerNetwork(AsyncSandboxNetwork):
    """Async computer-bound network."""

    _resource_type = "computer"


__all__ = [
    "AsyncComputerNetwork",
    "AsyncEgressNetwork",
    "AsyncSandboxNetwork",
    "ComputerNetwork",
    "EgressNetwork",
    "SandboxNetwork",
]
