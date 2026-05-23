"""Admin resource — /api/v1/admin/* endpoints.

Requires an admin credential: a ``msk_a_*`` / ``msk_p_*`` API key or an
admin JWT. Calls from a user-role credential return ``PermissionError``.

The methods exposed here wrap the highest-value admin operations. For
anything not covered, drop down to :meth:`Admin.request` which accepts
an arbitrary method + path pair.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _maybe(params: Dict[str, Any], **kw: Any) -> Dict[str, Any]:
    """Drop keys whose value is ``None`` before sending as query params."""
    params.update({k: v for k, v in kw.items() if v is not None})
    return params


class Admin:
    """Synchronous admin surface."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    # -- escape hatch --------------------------------------------------------

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Call any admin endpoint directly.

        ``path`` is relative to ``/api/v1``; the leading ``/admin`` prefix
        is expected (e.g. ``/admin/dashboard``).
        """
        return self._transport.request(method, path, json_body=json_body, params=params)

    # -- overview ------------------------------------------------------------

    def dashboard(self) -> Dict[str, Any]:
        return self._transport.request("GET", "/admin/dashboard")

    def stats(self) -> Dict[str, Any]:
        return self._transport.request("GET", "/admin/stats")

    def audit_log(self, *, limit: int = 20, cursor: Optional[str] = None) -> Dict[str, Any]:
        return self._transport.request(
            "GET", "/admin/audit-log", params=_maybe({"limit": limit}, cursor=cursor)
        )

    def detailed_health(self) -> Dict[str, Any]:
        return self._transport.request("GET", "/admin/health/detailed")

    # -- credits -------------------------------------------------------------

    def grant_credits(
        self,
        tenant_id: str,
        amount: int,
        description: str,
        *,
        expires_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        body = _maybe(
            {"tenant_id": tenant_id, "amount": amount, "description": description},
            expires_at=expires_at,
        )
        return self._transport.request("POST", "/admin/credits/grant", json_body=body)

    def deduct_credits(self, tenant_id: str, amount: int, description: str) -> Dict[str, Any]:
        body = {"tenant_id": tenant_id, "amount": amount, "description": description}
        return self._transport.request("POST", "/admin/credits/deduct", json_body=body)

    def refund_credits(
        self,
        tenant_id: str,
        amount: int,
        description: str,
        *,
        transaction_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        body = _maybe(
            {"tenant_id": tenant_id, "amount": amount, "description": description},
            transaction_id=transaction_id,
        )
        return self._transport.request("POST", "/admin/credits/refund", json_body=body)

    def tenant_balance(self, tenant_id: str) -> Dict[str, Any]:
        return self._transport.request("GET", f"/admin/credits/{tenant_id}/balance")

    def tenant_credit_history(
        self, tenant_id: str, *, limit: int = 20, cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        return self._transport.request(
            "GET",
            f"/admin/credits/{tenant_id}/history",
            params=_maybe({"limit": limit}, cursor=cursor),
        )

    # -- users ---------------------------------------------------------------

    def list_users(
        self,
        *,
        limit: int = 20,
        cursor: Optional[str] = None,
        q: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._transport.request(
            "GET",
            "/admin/users",
            params=_maybe({"limit": limit}, cursor=cursor, q=q, status=status),
        )

    def get_user(self, user_id: str) -> Dict[str, Any]:
        return self._transport.request("GET", f"/admin/users/{user_id}")

    def update_user(self, user_id: str, **attrs: Any) -> Dict[str, Any]:
        return self._transport.request("PUT", f"/admin/users/{user_id}", json_body=attrs)

    def delete_user(self, user_id: str) -> Dict[str, Any]:
        return self._transport.request("DELETE", f"/admin/users/{user_id}")

    def change_user_role(self, user_id: str, role: str) -> Dict[str, Any]:
        return self._transport.request(
            "POST", f"/admin/users/{user_id}/role", json_body={"role": role}
        )

    def force_logout(self, user_id: str) -> Dict[str, Any]:
        return self._transport.request("POST", f"/admin/users/{user_id}/force-logout")

    def suspend_user(self, user_id: str, *, reason: Optional[str] = None) -> Dict[str, Any]:
        return self._transport.request(
            "POST", f"/admin/users/{user_id}/suspend", json_body=_maybe({}, reason=reason)
        )

    def unsuspend_user(self, user_id: str) -> Dict[str, Any]:
        return self._transport.request("POST", f"/admin/users/{user_id}/unsuspend")

    def ban_user(
        self, user_id: str, reason: str, *, expires_at: Optional[str] = None
    ) -> Dict[str, Any]:
        return self._transport.request(
            "POST",
            f"/admin/users/{user_id}/ban",
            json_body=_maybe({"reason": reason}, expires_at=expires_at),
        )

    def unban_user(self, user_id: str) -> Dict[str, Any]:
        return self._transport.request("POST", f"/admin/users/{user_id}/unban")

    def bulk_user_action(
        self,
        user_ids: List[str],
        action: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        body = _maybe({"user_ids": user_ids, "action": action}, params=params)
        return self._transport.request("POST", "/admin/users/bulk", json_body=body)

    # -- tenants -------------------------------------------------------------

    def list_tenants(
        self, *, limit: int = 20, cursor: Optional[str] = None, q: Optional[str] = None
    ) -> Dict[str, Any]:
        return self._transport.request(
            "GET", "/admin/tenants", params=_maybe({"limit": limit}, cursor=cursor, q=q)
        )

    def tenant_detail(self, tenant_id: str) -> Dict[str, Any]:
        return self._transport.request("GET", f"/admin/tenants/{tenant_id}/detail")

    def suspend_tenant(
        self, tenant_id: str, *, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        return self._transport.request(
            "POST", f"/admin/tenants/{tenant_id}/suspend", json_body=_maybe({}, reason=reason)
        )

    def unsuspend_tenant(self, tenant_id: str) -> Dict[str, Any]:
        return self._transport.request("POST", f"/admin/tenants/{tenant_id}/unsuspend")

    def change_tenant_plan(
        self, tenant_id: str, plan: str, *, prorate: bool = True
    ) -> Dict[str, Any]:
        return self._transport.request(
            "POST",
            f"/admin/tenants/{tenant_id}/plan",
            json_body={"plan": plan, "prorate": prorate},
        )

    def delete_tenant(self, tenant_id: str) -> Dict[str, Any]:
        return self._transport.request("DELETE", f"/admin/tenants/{tenant_id}")

    # -- computers -----------------------------------------------------------

    def list_computers(
        self,
        *,
        limit: int = 20,
        cursor: Optional[str] = None,
        status: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._transport.request(
            "GET",
            "/admin/computers",
            params=_maybe({"limit": limit}, cursor=cursor, status=status, tenant_id=tenant_id),
        )

    def delete_computer(self, computer_id: str) -> Dict[str, Any]:
        return self._transport.request("DELETE", f"/admin/computers/{computer_id}")

    def suspend_computer(self, computer_id: str) -> Dict[str, Any]:
        return self._transport.request("POST", f"/admin/computers/{computer_id}/suspend")

    def resume_computer(self, computer_id: str) -> Dict[str, Any]:
        return self._transport.request("POST", f"/admin/computers/{computer_id}/resume")

    def restart_computer(self, computer_id: str) -> Dict[str, Any]:
        return self._transport.request("POST", f"/admin/computers/{computer_id}/restart")

    def purge_stale_computers(self) -> Dict[str, Any]:
        return self._transport.request("POST", "/admin/computers/purge-stale")

    # -- api keys ------------------------------------------------------------

    def list_api_keys(
        self,
        *,
        limit: int = 20,
        cursor: Optional[str] = None,
        tenant_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._transport.request(
            "GET",
            "/admin/api-keys",
            params=_maybe({"limit": limit}, cursor=cursor, tenant_id=tenant_id, status=status),
        )

    def create_api_key(
        self,
        name: str,
        tenant_id: str,
        user_id: str,
        *,
        key_type: str = "user",
        purpose: str = "api",
        rate_limit_rpm: Optional[int] = None,
        expires_at: Optional[str] = None,
        allowed_ips: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        body = _maybe(
            {
                "name": name,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "key_type": key_type,
                "purpose": purpose,
            },
            rate_limit_rpm=rate_limit_rpm,
            expires_at=expires_at,
            allowed_ips=allowed_ips,
        )
        return self._transport.request("POST", "/admin/api-keys", json_body=body)

    def api_key_stats(self) -> Dict[str, Any]:
        return self._transport.request("GET", "/admin/api-keys/stats")

    def bulk_revoke_api_keys(self, key_ids: List[str]) -> Dict[str, Any]:
        return self._transport.request(
            "POST", "/admin/api-keys/bulk-revoke", json_body={"key_ids": key_ids}
        )

    def revoke_api_key(self, key_id: str) -> Dict[str, Any]:
        return self._transport.request("DELETE", f"/admin/api-keys/{key_id}")

    # -- optimal -------------------------------------------------------------

    def optimal_status(self) -> Dict[str, Any]:
        return self._transport.request("GET", "/admin/optimal/status")

    def list_optimal_models(self) -> Dict[str, Any]:
        return self._transport.request("GET", "/admin/optimal/models")

    def switch_optimal_model(self, model_id: str) -> Dict[str, Any]:
        return self._transport.request(
            "POST", "/admin/optimal/models/switch", json_body={"model_id": model_id}
        )


class AsyncAdmin:
    """Asynchronous admin surface — mirrors :class:`Admin`."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        return await self._transport.request(method, path, json_body=json_body, params=params)

    async def dashboard(self) -> Dict[str, Any]:
        return await self._transport.request("GET", "/admin/dashboard")

    async def stats(self) -> Dict[str, Any]:
        return await self._transport.request("GET", "/admin/stats")

    async def audit_log(self, *, limit: int = 20, cursor: Optional[str] = None) -> Dict[str, Any]:
        return await self._transport.request(
            "GET", "/admin/audit-log", params=_maybe({"limit": limit}, cursor=cursor)
        )

    async def detailed_health(self) -> Dict[str, Any]:
        return await self._transport.request("GET", "/admin/health/detailed")

    async def grant_credits(
        self,
        tenant_id: str,
        amount: int,
        description: str,
        *,
        expires_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        body = _maybe(
            {"tenant_id": tenant_id, "amount": amount, "description": description},
            expires_at=expires_at,
        )
        return await self._transport.request("POST", "/admin/credits/grant", json_body=body)

    async def deduct_credits(
        self, tenant_id: str, amount: int, description: str
    ) -> Dict[str, Any]:
        body = {"tenant_id": tenant_id, "amount": amount, "description": description}
        return await self._transport.request("POST", "/admin/credits/deduct", json_body=body)

    async def refund_credits(
        self,
        tenant_id: str,
        amount: int,
        description: str,
        *,
        transaction_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        body = _maybe(
            {"tenant_id": tenant_id, "amount": amount, "description": description},
            transaction_id=transaction_id,
        )
        return await self._transport.request("POST", "/admin/credits/refund", json_body=body)

    async def tenant_balance(self, tenant_id: str) -> Dict[str, Any]:
        return await self._transport.request("GET", f"/admin/credits/{tenant_id}/balance")

    async def tenant_credit_history(
        self, tenant_id: str, *, limit: int = 20, cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self._transport.request(
            "GET",
            f"/admin/credits/{tenant_id}/history",
            params=_maybe({"limit": limit}, cursor=cursor),
        )

    async def list_users(
        self,
        *,
        limit: int = 20,
        cursor: Optional[str] = None,
        q: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._transport.request(
            "GET",
            "/admin/users",
            params=_maybe({"limit": limit}, cursor=cursor, q=q, status=status),
        )

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        return await self._transport.request("GET", f"/admin/users/{user_id}")

    async def update_user(self, user_id: str, **attrs: Any) -> Dict[str, Any]:
        return await self._transport.request("PUT", f"/admin/users/{user_id}", json_body=attrs)

    async def delete_user(self, user_id: str) -> Dict[str, Any]:
        return await self._transport.request("DELETE", f"/admin/users/{user_id}")

    async def change_user_role(self, user_id: str, role: str) -> Dict[str, Any]:
        return await self._transport.request(
            "POST", f"/admin/users/{user_id}/role", json_body={"role": role}
        )

    async def force_logout(self, user_id: str) -> Dict[str, Any]:
        return await self._transport.request("POST", f"/admin/users/{user_id}/force-logout")

    async def suspend_user(
        self, user_id: str, *, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self._transport.request(
            "POST", f"/admin/users/{user_id}/suspend", json_body=_maybe({}, reason=reason)
        )

    async def unsuspend_user(self, user_id: str) -> Dict[str, Any]:
        return await self._transport.request("POST", f"/admin/users/{user_id}/unsuspend")

    async def ban_user(
        self, user_id: str, reason: str, *, expires_at: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self._transport.request(
            "POST",
            f"/admin/users/{user_id}/ban",
            json_body=_maybe({"reason": reason}, expires_at=expires_at),
        )

    async def unban_user(self, user_id: str) -> Dict[str, Any]:
        return await self._transport.request("POST", f"/admin/users/{user_id}/unban")

    async def bulk_user_action(
        self,
        user_ids: List[str],
        action: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        body = _maybe({"user_ids": user_ids, "action": action}, params=params)
        return await self._transport.request("POST", "/admin/users/bulk", json_body=body)

    async def list_tenants(
        self, *, limit: int = 20, cursor: Optional[str] = None, q: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self._transport.request(
            "GET", "/admin/tenants", params=_maybe({"limit": limit}, cursor=cursor, q=q)
        )

    async def tenant_detail(self, tenant_id: str) -> Dict[str, Any]:
        return await self._transport.request("GET", f"/admin/tenants/{tenant_id}/detail")

    async def suspend_tenant(
        self, tenant_id: str, *, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self._transport.request(
            "POST", f"/admin/tenants/{tenant_id}/suspend", json_body=_maybe({}, reason=reason)
        )

    async def unsuspend_tenant(self, tenant_id: str) -> Dict[str, Any]:
        return await self._transport.request("POST", f"/admin/tenants/{tenant_id}/unsuspend")

    async def change_tenant_plan(
        self, tenant_id: str, plan: str, *, prorate: bool = True
    ) -> Dict[str, Any]:
        return await self._transport.request(
            "POST",
            f"/admin/tenants/{tenant_id}/plan",
            json_body={"plan": plan, "prorate": prorate},
        )

    async def delete_tenant(self, tenant_id: str) -> Dict[str, Any]:
        return await self._transport.request("DELETE", f"/admin/tenants/{tenant_id}")

    async def list_computers(
        self,
        *,
        limit: int = 20,
        cursor: Optional[str] = None,
        status: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._transport.request(
            "GET",
            "/admin/computers",
            params=_maybe({"limit": limit}, cursor=cursor, status=status, tenant_id=tenant_id),
        )

    async def delete_computer(self, computer_id: str) -> Dict[str, Any]:
        return await self._transport.request("DELETE", f"/admin/computers/{computer_id}")

    async def suspend_computer(self, computer_id: str) -> Dict[str, Any]:
        return await self._transport.request("POST", f"/admin/computers/{computer_id}/suspend")

    async def resume_computer(self, computer_id: str) -> Dict[str, Any]:
        return await self._transport.request("POST", f"/admin/computers/{computer_id}/resume")

    async def restart_computer(self, computer_id: str) -> Dict[str, Any]:
        return await self._transport.request("POST", f"/admin/computers/{computer_id}/restart")

    async def purge_stale_computers(self) -> Dict[str, Any]:
        return await self._transport.request("POST", "/admin/computers/purge-stale")

    async def list_api_keys(
        self,
        *,
        limit: int = 20,
        cursor: Optional[str] = None,
        tenant_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._transport.request(
            "GET",
            "/admin/api-keys",
            params=_maybe({"limit": limit}, cursor=cursor, tenant_id=tenant_id, status=status),
        )

    async def create_api_key(
        self,
        name: str,
        tenant_id: str,
        user_id: str,
        *,
        key_type: str = "user",
        purpose: str = "api",
        rate_limit_rpm: Optional[int] = None,
        expires_at: Optional[str] = None,
        allowed_ips: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        body = _maybe(
            {
                "name": name,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "key_type": key_type,
                "purpose": purpose,
            },
            rate_limit_rpm=rate_limit_rpm,
            expires_at=expires_at,
            allowed_ips=allowed_ips,
        )
        return await self._transport.request("POST", "/admin/api-keys", json_body=body)

    async def api_key_stats(self) -> Dict[str, Any]:
        return await self._transport.request("GET", "/admin/api-keys/stats")

    async def bulk_revoke_api_keys(self, key_ids: List[str]) -> Dict[str, Any]:
        return await self._transport.request(
            "POST", "/admin/api-keys/bulk-revoke", json_body={"key_ids": key_ids}
        )

    async def revoke_api_key(self, key_id: str) -> Dict[str, Any]:
        return await self._transport.request("DELETE", f"/admin/api-keys/{key_id}")

    async def optimal_status(self) -> Dict[str, Any]:
        return await self._transport.request("GET", "/admin/optimal/status")

    async def list_optimal_models(self) -> Dict[str, Any]:
        return await self._transport.request("GET", "/admin/optimal/models")

    async def switch_optimal_model(self, model_id: str) -> Dict[str, Any]:
        return await self._transport.request(
            "POST", "/admin/optimal/models/switch", json_body={"model_id": model_id}
        )
