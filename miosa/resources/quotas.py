"""Quotas — per-external-user resource caps."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data", "quota", "quotas")) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class Quotas:
    """Tenant quota management — per ``external_user_id`` resource caps.

    Example::

        client.quotas.set("usr_123", max_sandboxes=5, max_concurrent=2)
        current = client.quotas.get("usr_123")
        client.quotas.delete("usr_123")  # revert to tenant default
    """

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def get(self, external_user_id: str) -> Dict[str, Any]:
        """GET /api/v1/quotas/external/{external_user_id} — current limits + usage."""
        return _unwrap(
            self._t.request("GET", f"/quotas/external/{external_user_id}")
        )

    def set(
        self,
        external_user_id: str,
        *,
        max_sandboxes: Optional[int] = None,
        max_concurrent: Optional[int] = None,
        max_storage_gb: Optional[int] = None,
        max_credit_cents: Optional[int] = None,
    ) -> Dict[str, Any]:
        """PUT /api/v1/quotas/external/{external_user_id} — update limits.

        Args:
            external_user_id: White-label user identifier.
            max_sandboxes: Maximum total sandboxes this user can own.
            max_concurrent: Maximum sandboxes running at one time.
            max_storage_gb: Maximum persistent storage in GB.
            max_credit_cents: Maximum spendable credits in cents.
        """
        body: Dict[str, Any] = {}
        for key, value in (
            ("max_sandboxes", max_sandboxes),
            ("max_concurrent", max_concurrent),
            ("max_storage_gb", max_storage_gb),
            ("max_credit_cents", max_credit_cents),
        ):
            if value is not None:
                body[key] = value
        return _unwrap(
            self._t.request("PUT", f"/quotas/external/{external_user_id}", json_body=body)
        )

    def delete(self, external_user_id: str) -> None:
        """DELETE /api/v1/quotas/external/{external_user_id} — revert to tenant default."""
        self._t.request("DELETE", f"/quotas/external/{external_user_id}")


class AsyncQuotas:
    """Async quota management."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def get(self, external_user_id: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request("GET", f"/quotas/external/{external_user_id}")
        )

    async def set(
        self,
        external_user_id: str,
        *,
        max_sandboxes: Optional[int] = None,
        max_concurrent: Optional[int] = None,
        max_storage_gb: Optional[int] = None,
        max_credit_cents: Optional[int] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {}
        for key, value in (
            ("max_sandboxes", max_sandboxes),
            ("max_concurrent", max_concurrent),
            ("max_storage_gb", max_storage_gb),
            ("max_credit_cents", max_credit_cents),
        ):
            if value is not None:
                body[key] = value
        return _unwrap(
            await self._t.request("PUT", f"/quotas/external/{external_user_id}", json_body=body)
        )

    async def delete(self, external_user_id: str) -> None:
        await self._t.request("DELETE", f"/quotas/external/{external_user_id}")
