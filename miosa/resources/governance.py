"""Phase 6 governance resources — policy, members, workspaces, bulk ops, billing, impersonation."""

from __future__ import annotations

import json as _json
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from ..types import Computer as ComputerModel
from ..types import WorkspaceData
from .tenant import AsyncBranding, AsyncPreviewDomain, Branding, PreviewDomain

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, *keys: str) -> Any:
    if isinstance(data, dict):
        for k in keys or ("data",):
            if k in data:
                return data[k]
    return data


# ── Effective policy typed wrapper ────────────────────────────────────────────

class _FieldValue:
    """Typed accessor for an effective-policy field: .value and .source."""

    def __init__(self, data: Any) -> None:
        self._data = data if isinstance(data, dict) else {}

    @property
    def value(self) -> Any:
        return self._data.get("value")

    @property
    def source(self) -> str:
        return self._data.get("source", "platform")

    def __repr__(self) -> str:
        return f"FieldValue(value={self.value!r}, source={self.source!r})"


class _PolicySection:
    """Wraps one section of an effective policy (e.g. lifecycle, quotas)."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data

    def __getattr__(self, name: str) -> "_FieldValue":
        if name.startswith("_"):
            raise AttributeError(name)
        return _FieldValue(self._data.get(name, {}))

    def __repr__(self) -> str:
        return f"PolicySection({self._data!r})"


class EffectivePolicy:
    """Typed wrapper around the effective-policy response.

    Usage::

        eff = client.external_users("alice").policy.effective()
        print(eff.lifecycle.default_idle_timeout_sec.value)  # 600
        print(eff.lifecycle.default_idle_timeout_sec.source)  # "user"
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data

    def __getattr__(self, name: str) -> "_PolicySection":
        if name.startswith("_"):
            raise AttributeError(name)
        return _PolicySection(self._data.get(name, {}))

    def raw(self) -> Dict[str, Any]:
        """Return the raw response dict."""
        return self._data

    def __repr__(self) -> str:
        keys = list(self._data.keys())
        return f"EffectivePolicy(sections={keys!r})"


# ── Policy sub-resources ──────────────────────────────────────────────────────

class TenantPolicy:
    def __init__(self, t: "SyncTransport") -> None:
        self._t = t

    def get(self) -> Dict[str, Any]:
        """GET /api/v1/tenant/policy"""
        return _unwrap(self._t.request("GET", "/tenant/policy"), "data", "policy")

    def set(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        """PUT /api/v1/tenant/policy"""
        return _unwrap(self._t.request("PUT", "/tenant/policy", json_body=policy), "data", "policy")

    def delete(self) -> None:
        """DELETE /api/v1/tenant/policy"""
        self._t.request("DELETE", "/tenant/policy")


class AsyncTenantPolicy:
    def __init__(self, t: "AsyncTransport") -> None:
        self._t = t

    async def get(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", "/tenant/policy"), "data", "policy")

    async def set(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        return _unwrap(await self._t.request("PUT", "/tenant/policy", json_body=policy), "data", "policy")

    async def delete(self) -> None:
        await self._t.request("DELETE", "/tenant/policy")


class WorkspacePolicy:
    def __init__(self, t: "SyncTransport", workspace_id: str) -> None:
        self._t = t
        self._id = workspace_id

    def get(self) -> Dict[str, Any]:
        return _unwrap(self._t.request("GET", f"/workspaces/{self._id}/policy"), "data", "policy")

    def set(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        return _unwrap(self._t.request("PUT", f"/workspaces/{self._id}/policy", json_body=policy), "data", "policy")

    def delete(self) -> None:
        self._t.request("DELETE", f"/workspaces/{self._id}/policy")


class AsyncWorkspacePolicy:
    def __init__(self, t: "AsyncTransport", workspace_id: str) -> None:
        self._t = t
        self._id = workspace_id

    async def get(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", f"/workspaces/{self._id}/policy"), "data", "policy")

    async def set(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        return _unwrap(await self._t.request("PUT", f"/workspaces/{self._id}/policy", json_body=policy), "data", "policy")

    async def delete(self) -> None:
        await self._t.request("DELETE", f"/workspaces/{self._id}/policy")


class ExternalUserPolicy:
    def __init__(self, t: "SyncTransport", external_user_id: str) -> None:
        self._t = t
        self._uid = external_user_id

    def get(self) -> Dict[str, Any]:
        return _unwrap(self._t.request("GET", f"/external-users/{self._uid}/policy"), "data", "policy")

    def set(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        return _unwrap(self._t.request("PUT", f"/external-users/{self._uid}/policy", json_body=policy), "data", "policy")

    def delete(self) -> None:
        self._t.request("DELETE", f"/external-users/{self._uid}/policy")

    def effective(self) -> EffectivePolicy:
        """GET /api/v1/external-users/{id}/effective-policy → EffectivePolicy"""
        raw = self._t.request("GET", f"/external-users/{self._uid}/effective-policy")
        data = _unwrap(raw, "data", "policy") if isinstance(raw, dict) else raw
        return EffectivePolicy(data if isinstance(data, dict) else raw)


class AsyncExternalUserPolicy:
    def __init__(self, t: "AsyncTransport", external_user_id: str) -> None:
        self._t = t
        self._uid = external_user_id

    async def get(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", f"/external-users/{self._uid}/policy"), "data", "policy")

    async def set(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        return _unwrap(await self._t.request("PUT", f"/external-users/{self._uid}/policy", json_body=policy), "data", "policy")

    async def delete(self) -> None:
        await self._t.request("DELETE", f"/external-users/{self._uid}/policy")

    async def effective(self) -> EffectivePolicy:
        raw = await self._t.request("GET", f"/external-users/{self._uid}/effective-policy")
        data = _unwrap(raw, "data", "policy") if isinstance(raw, dict) else raw
        return EffectivePolicy(data if isinstance(data, dict) else raw)


# ── ExternalUsers proxy ───────────────────────────────────────────────────────

class _ExternalUserProxy:
    """client.external_users("uid") — returns an object with .policy sub-resource."""

    def __init__(self, t: "SyncTransport", external_user_id: str) -> None:
        self.policy = ExternalUserPolicy(t, external_user_id)


class _AsyncExternalUserProxy:
    def __init__(self, t: "AsyncTransport", external_user_id: str) -> None:
        self.policy = AsyncExternalUserPolicy(t, external_user_id)


class ExternalUsers:
    """client.external_users('uid') gateway."""

    def __init__(self, t: "SyncTransport") -> None:
        self._t = t

    def __call__(self, external_user_id: str) -> "_ExternalUserProxy":
        return _ExternalUserProxy(self._t, external_user_id)


class AsyncExternalUsers:
    def __init__(self, t: "AsyncTransport") -> None:
        self._t = t

    def __call__(self, external_user_id: str) -> "_AsyncExternalUserProxy":
        return _AsyncExternalUserProxy(self._t, external_user_id)


# ── Tenant members ────────────────────────────────────────────────────────────

class TenantMembers:
    def __init__(self, t: "SyncTransport") -> None:
        self._t = t

    def list(self) -> List[Dict[str, Any]]:
        data = self._t.request("GET", "/tenant/members")
        return _unwrap(data, "data", "members") or []

    def invite(self, email: str, role: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("POST", "/tenant/members", json_body={"email": email, "role": role}), "data")

    def update_role(self, member_id: str, role: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("PATCH", f"/tenant/members/{member_id}/role", json_body={"role": role}), "data")

    def remove(self, member_id: str) -> None:
        self._t.request("DELETE", f"/tenant/members/{member_id}")

    def transfer_ownership(self, new_owner_user_id: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("POST", "/tenant/transfer-ownership", json_body={"new_owner_user_id": new_owner_user_id}), "data")


class AsyncTenantMembers:
    def __init__(self, t: "AsyncTransport") -> None:
        self._t = t

    async def list(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", "/tenant/members")
        return _unwrap(data, "data", "members") or []

    async def invite(self, email: str, role: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("POST", "/tenant/members", json_body={"email": email, "role": role}), "data")

    async def update_role(self, member_id: str, role: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("PATCH", f"/tenant/members/{member_id}/role", json_body={"role": role}), "data")

    async def remove(self, member_id: str) -> None:
        await self._t.request("DELETE", f"/tenant/members/{member_id}")

    async def transfer_ownership(self, new_owner_user_id: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("POST", "/tenant/transfer-ownership", json_body={"new_owner_user_id": new_owner_user_id}), "data")


# ── Tenant events stream ──────────────────────────────────────────────────────

def _parse_sse(raw: Dict[str, Any]) -> Dict[str, Any]:
    data_str = raw.get("data", "")
    try:
        payload: Any = _json.loads(data_str) if isinstance(data_str, str) else data_str
    except (_json.JSONDecodeError, TypeError):
        payload = {"raw": data_str}
    if not isinstance(payload, dict):
        payload = {"raw": payload}
    payload.setdefault("_event_type", raw.get("event", "message"))
    return payload


class TenantEventStream:
    def __init__(self, t: "SyncTransport") -> None:
        self._t = t

    def stream(
        self,
        *,
        types: Optional[List[str]] = None,
        scope: Optional[str] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Stream admin events via SSE. ``scope`` = all|workspace:{id}|external_user:{id}."""
        params: Dict[str, Any] = {}
        if types:
            params["types"] = ",".join(types)
        if scope:
            params["scope"] = scope
        for raw in self._t.stream_sse("/tenant/events/stream", params=params or None):
            yield _parse_sse(raw)


class AsyncTenantEventStream:
    def __init__(self, t: "AsyncTransport") -> None:
        self._t = t

    async def stream(
        self,
        *,
        types: Optional[List[str]] = None,
        scope: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if types:
            params["types"] = ",".join(types)
        if scope:
            params["scope"] = scope
        async for raw in self._t.stream_sse("/tenant/events/stream", params=params or None):
            yield _parse_sse(raw)


# ── Workspace members ─────────────────────────────────────────────────────────

class WorkspaceMembers2:
    """Per-workspace member management (Phase 6 complement to top-level workspace_members)."""

    def __init__(self, t: "SyncTransport", workspace_id: str) -> None:
        self._t = t
        self._id = workspace_id

    def list(self) -> List[Dict[str, Any]]:
        data = self._t.request("GET", f"/workspaces/{self._id}/members")
        return _unwrap(data, "data", "members") or []

    def invite(self, email: str, role: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("POST", f"/workspaces/{self._id}/members", json_body={"email": email, "role": role}), "data")

    def update_role(self, member_id: str, role: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("PATCH", f"/workspaces/{self._id}/members/{member_id}/role", json_body={"role": role}), "data")

    def remove(self, member_id: str) -> None:
        self._t.request("DELETE", f"/workspaces/{self._id}/members/{member_id}")


class AsyncWorkspaceMembers2:
    def __init__(self, t: "AsyncTransport", workspace_id: str) -> None:
        self._t = t
        self._id = workspace_id

    async def list(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", f"/workspaces/{self._id}/members")
        return _unwrap(data, "data", "members") or []

    async def invite(self, email: str, role: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("POST", f"/workspaces/{self._id}/members", json_body={"email": email, "role": role}), "data")

    async def update_role(self, member_id: str, role: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("PATCH", f"/workspaces/{self._id}/members/{member_id}/role", json_body={"role": role}), "data")

    async def remove(self, member_id: str) -> None:
        await self._t.request("DELETE", f"/workspaces/{self._id}/members/{member_id}")


# ── Workspace transfer ────────────────────────────────────────────────────────

class WorkspaceTransfer:
    def __init__(self, t: "SyncTransport", workspace_id: str) -> None:
        self._t = t
        self._id = workspace_id

    def transfer(self, resource_ids: List[str], target_workspace_id: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("POST", f"/workspaces/{self._id}/transfer", json_body={"resource_ids": resource_ids, "target_workspace_id": target_workspace_id}), "data")


class AsyncWorkspaceTransfer:
    def __init__(self, t: "AsyncTransport", workspace_id: str) -> None:
        self._t = t
        self._id = workspace_id

    async def transfer(self, resource_ids: List[str], target_workspace_id: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("POST", f"/workspaces/{self._id}/transfer", json_body={"resource_ids": resource_ids, "target_workspace_id": target_workspace_id}), "data")


# ── WorkspacesProxy (client.workspaces(id) gateway) ───────────────────────────

class _WorkspaceProxy:
    """client.workspaces('id') — returns an object with .policy and .members."""

    def __init__(self, t: "SyncTransport", workspace_id: str) -> None:
        self.policy = WorkspacePolicy(t, workspace_id)
        self.members = WorkspaceMembers2(t, workspace_id)
        self._transfer = WorkspaceTransfer(t, workspace_id)

    def transfer(self, resource_ids: List[str], target_workspace_id: str) -> Dict[str, Any]:
        return self._transfer.transfer(resource_ids, target_workspace_id)


class _AsyncWorkspaceProxy:
    def __init__(self, t: "AsyncTransport", workspace_id: str) -> None:
        self.policy = AsyncWorkspacePolicy(t, workspace_id)
        self.members = AsyncWorkspaceMembers2(t, workspace_id)
        self._transfer = AsyncWorkspaceTransfer(t, workspace_id)

    async def transfer(self, resource_ids: List[str], target_workspace_id: str) -> Dict[str, Any]:
        return await self._transfer.transfer(resource_ids, target_workspace_id)


# ── Bulk ops ──────────────────────────────────────────────────────────────────

class BulkSandboxes:
    def __init__(self, t: "SyncTransport") -> None:
        self._t = t

    def pause(self, *, ids: Optional[List[str]] = None, filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._t.request("POST", "/bulk/sandboxes/pause", json_body=_bulk_body(ids, filter))

    def resume(self, *, ids: Optional[List[str]] = None, filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._t.request("POST", "/bulk/sandboxes/resume", json_body=_bulk_body(ids, filter))

    def destroy(self, *, ids: Optional[List[str]] = None, filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._t.request("POST", "/bulk/sandboxes/destroy", json_body=_bulk_body(ids, filter))


class AsyncBulkSandboxes:
    def __init__(self, t: "AsyncTransport") -> None:
        self._t = t

    async def pause(self, *, ids: Optional[List[str]] = None, filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self._t.request("POST", "/bulk/sandboxes/pause", json_body=_bulk_body(ids, filter))

    async def resume(self, *, ids: Optional[List[str]] = None, filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self._t.request("POST", "/bulk/sandboxes/resume", json_body=_bulk_body(ids, filter))

    async def destroy(self, *, ids: Optional[List[str]] = None, filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self._t.request("POST", "/bulk/sandboxes/destroy", json_body=_bulk_body(ids, filter))


def _bulk_body(ids: Optional[List[str]], filter: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if ids is not None:
        return {"ids": ids}
    if filter is not None:
        return {"filter": filter}
    raise ValueError("Provide either ids= or filter=")


class BulkPolicy:
    def __init__(self, t: "SyncTransport") -> None:
        self._t = t

    def apply(self, *, tier: str, ids_or_filter: Union[List[str], Dict[str, Any]], policy: Dict[str, Any]) -> Dict[str, Any]:
        body: Dict[str, Any] = {"tier": tier, "policy": policy}
        if isinstance(ids_or_filter, list):
            body["ids"] = ids_or_filter
        else:
            body["filter"] = ids_or_filter
        return self._t.request("POST", "/bulk/policy/apply", json_body=body)


class AsyncBulkPolicy:
    def __init__(self, t: "AsyncTransport") -> None:
        self._t = t

    async def apply(self, *, tier: str, ids_or_filter: Union[List[str], Dict[str, Any]], policy: Dict[str, Any]) -> Dict[str, Any]:
        body: Dict[str, Any] = {"tier": tier, "policy": policy}
        if isinstance(ids_or_filter, list):
            body["ids"] = ids_or_filter
        else:
            body["filter"] = ids_or_filter
        return await self._t.request("POST", "/bulk/policy/apply", json_body=body)


class BulkJobs:
    def __init__(self, t: "SyncTransport") -> None:
        self._t = t

    def get(self, job_id: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("GET", f"/bulk/jobs/{job_id}"), "data", "job")


class AsyncBulkJobs:
    def __init__(self, t: "AsyncTransport") -> None:
        self._t = t

    async def get(self, job_id: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", f"/bulk/jobs/{job_id}"), "data", "job")


class Bulk:
    """client.bulk gateway."""

    def __init__(self, t: "SyncTransport") -> None:
        self.sandboxes = BulkSandboxes(t)
        self.policy = BulkPolicy(t)
        self.jobs = BulkJobs(t)


class AsyncBulk:
    def __init__(self, t: "AsyncTransport") -> None:
        self.sandboxes = AsyncBulkSandboxes(t)
        self.policy = AsyncBulkPolicy(t)
        self.jobs = AsyncBulkJobs(t)


# ── Billing ───────────────────────────────────────────────────────────────────

class BillingInvoices:
    def __init__(self, t: "SyncTransport") -> None:
        self._t = t

    def list(self, *, limit: int = 20, cursor: Optional[str] = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        data = self._t.request("GET", "/billing/invoices", params=params)
        return _unwrap(data, "data", "invoices") or []

    def get(self, invoice_id: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("GET", f"/billing/invoices/{invoice_id}"), "data", "invoice")


class AsyncBillingInvoices:
    def __init__(self, t: "AsyncTransport") -> None:
        self._t = t

    async def list(self, *, limit: int = 20, cursor: Optional[str] = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        data = await self._t.request("GET", "/billing/invoices", params=params)
        return _unwrap(data, "data", "invoices") or []

    async def get(self, invoice_id: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", f"/billing/invoices/{invoice_id}"), "data", "invoice")


class Billing:
    """client.billing gateway — invoices, payment_methods, upcoming."""

    def __init__(self, t: "SyncTransport") -> None:
        self._t = t
        self.invoices = BillingInvoices(t)

    def payment_methods(self) -> List[Dict[str, Any]]:
        data = self._t.request("GET", "/billing/payment-methods")
        return _unwrap(data, "data", "payment_methods") or []

    def upcoming(self) -> Dict[str, Any]:
        return _unwrap(self._t.request("GET", "/billing/upcoming"), "data", "invoice")


class AsyncBilling:
    def __init__(self, t: "AsyncTransport") -> None:
        self._t = t
        self.invoices = AsyncBillingInvoices(t)

    async def payment_methods(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", "/billing/payment-methods")
        return _unwrap(data, "data", "payment_methods") or []

    async def upcoming(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", "/billing/upcoming"), "data", "invoice")


# ── GovernanceTenant (wraps tenant.policy, tenant.members, tenant.events) ─────

class GovernanceTenant:
    """Extends the base Tenant resource with Phase 6 governance sub-resources.

    Mounted as ``client.tenant`` — gives access to:
    - ``client.tenant.policy.{get,set,delete}``
    - ``client.tenant.members.{list,invite,update_role,remove,transfer_ownership}``
    - ``client.tenant.events.stream(types=, scope=)``
    """

    def __init__(self, t: "SyncTransport") -> None:
        self._t = t
        self.preview_domain = PreviewDomain(t)
        self.branding = Branding(t)
        self.policy = TenantPolicy(t)
        self.members = TenantMembers(t)
        self.events = TenantEventStream(t)

    def current(self) -> Dict[str, Any]:
        return _unwrap(self._t.request("GET", "/tenant/plan"), "data", "tenant")


class AsyncGovernanceTenant:
    def __init__(self, t: "AsyncTransport") -> None:
        self._t = t
        self.preview_domain = AsyncPreviewDomain(t)
        self.branding = AsyncBranding(t)
        self.policy = AsyncTenantPolicy(t)
        self.members = AsyncTenantMembers(t)
        self.events = AsyncTenantEventStream(t)

    async def current(self) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", "/tenant/plan"), "data", "tenant")


# ── GovernanceWorkspaces (wraps existing Workspaces + per-ID proxy) ───────────

class GovernanceWorkspaces:
    """client.workspaces — list/create/get/update/delete + per-ID sub-resources.

    Usage::

        client.workspaces.list()
        client.workspaces("ws_123").policy.get()
        client.workspaces("ws_123").members.invite("alice@example.com", "developer")
        client.workspaces("ws_123").transfer(["sbx_1"], "ws_456")
    """

    def __init__(self, t: "SyncTransport") -> None:
        self._t = t

    def __call__(self, workspace_id: str) -> "_WorkspaceProxy":
        return _WorkspaceProxy(self._t, workspace_id)

    def list(self) -> List[WorkspaceData]:
        data = self._t.request("GET", "/workspaces")
        items = _unwrap(data, "data")
        if isinstance(items, dict) and "workspaces" in items:
            items = items["workspaces"]
        return [WorkspaceData.model_validate(item) for item in (items or [])]

    def create(self, name: str, *, description: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> WorkspaceData:
        body: Dict[str, Any] = {"name": name}
        if description is not None:
            body["description"] = description
        if metadata is not None:
            body["metadata"] = metadata
        return WorkspaceData.model_validate(
            _unwrap(self._t.request("POST", "/workspaces", json_body=body), "data")
        )

    def get(self, workspace_id: str) -> WorkspaceData:
        return WorkspaceData.model_validate(
            _unwrap(self._t.request("GET", f"/workspaces/{workspace_id}"), "data")
        )

    def update(self, workspace_id: str, **fields: Any) -> WorkspaceData:
        return WorkspaceData.model_validate(
            _unwrap(
                self._t.request("PATCH", f"/workspaces/{workspace_id}", json_body=fields),
                "data",
            )
        )

    def delete(self, workspace_id: str) -> None:
        self._t.request("DELETE", f"/workspaces/{workspace_id}")

    def list_computers(self, workspace_id: str) -> List[Any]:
        from .computer import Computer

        data = self._t.request("GET", f"/workspaces/{workspace_id}/computers")
        items: list[Any] = []
        if isinstance(data, dict):
            items = data.get("computers") or data.get("data") or []
        elif isinstance(data, list):
            items = data
        return [Computer(self._t, ComputerModel.model_validate(item)) for item in items]


class AsyncGovernanceWorkspaces:
    def __init__(self, t: "AsyncTransport") -> None:
        self._t = t

    def __call__(self, workspace_id: str) -> "_AsyncWorkspaceProxy":
        return _AsyncWorkspaceProxy(self._t, workspace_id)

    async def list(self) -> List[WorkspaceData]:
        data = await self._t.request("GET", "/workspaces")
        items = _unwrap(data, "data")
        if isinstance(items, dict) and "workspaces" in items:
            items = items["workspaces"]
        return [WorkspaceData.model_validate(item) for item in (items or [])]

    async def create(self, name: str, *, description: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> WorkspaceData:
        body: Dict[str, Any] = {"name": name}
        if description is not None:
            body["description"] = description
        if metadata is not None:
            body["metadata"] = metadata
        return WorkspaceData.model_validate(
            _unwrap(await self._t.request("POST", "/workspaces", json_body=body), "data")
        )

    async def get(self, workspace_id: str) -> WorkspaceData:
        return WorkspaceData.model_validate(
            _unwrap(await self._t.request("GET", f"/workspaces/{workspace_id}"), "data")
        )

    async def update(self, workspace_id: str, **fields: Any) -> WorkspaceData:
        return WorkspaceData.model_validate(
            _unwrap(
                await self._t.request("PATCH", f"/workspaces/{workspace_id}", json_body=fields),
                "data",
            )
        )

    async def delete(self, workspace_id: str) -> None:
        await self._t.request("DELETE", f"/workspaces/{workspace_id}")
