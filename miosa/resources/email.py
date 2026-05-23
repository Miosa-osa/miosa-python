"""Email — admin email campaigns, templates, and inbox surfaces.

Routes live under ``/api/v1/admin/email-{campaigns,templates,inbox}/``
and require an admin credential (``msk_a_*`` / ``msk_p_*`` or admin
JWT).

The top-level :class:`Email` resource exposes three sub-namespaces:

``client.email.campaigns``  bulk email send-out lifecycle
``client.email.templates``  reusable templates (keyed by name)
``client.email.inbox``      inbound + outbound direct messages
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(
    data: Any,
    keys: tuple[str, ...] = (
        "data",
        "campaigns",
        "templates",
        "inbox",
        "deliveries",
        "items",
    ),
) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


# ── Sync sub-namespaces ────────────────────────────────────────────────


class _EmailCampaigns:
    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request(
            "GET", "/admin/email-campaigns", params=params or None
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def create(self, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            self._t.request("POST", "/admin/email-campaigns", json_body=body)
        )

    def recipient_count(self, **filters: Any) -> Dict[str, Any]:
        params = {k: v for k, v in filters.items() if v is not None}
        return _unwrap(
            self._t.request(
                "GET",
                "/admin/email-campaigns/recipient-count",
                params=params or None,
            )
        )

    def send(self, campaign_id: str, **opts: Any) -> Dict[str, Any]:
        body = {k: v for k, v in opts.items() if v is not None}
        return _unwrap(
            self._t.request(
                "POST",
                f"/admin/email-campaigns/{campaign_id}/send",
                json_body=body,
            )
        )

    def cancel(self, campaign_id: str) -> Dict[str, Any]:
        return _unwrap(
            self._t.request(
                "POST", f"/admin/email-campaigns/{campaign_id}/cancel"
            )
        )

    def deliveries(
        self, campaign_id: str, **filters: Any
    ) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request(
            "GET",
            f"/admin/email-campaigns/{campaign_id}/deliveries",
            params=params or None,
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []


class _EmailTemplates:
    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request(
            "GET", "/admin/email-templates", params=params or None
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def create(self, *, key: str, **attrs: Any) -> Dict[str, Any]:
        body = {"key": key, **{k: v for k, v in attrs.items() if v is not None}}
        return _unwrap(
            self._t.request("POST", "/admin/email-templates", json_body=body)
        )

    def update(self, key: str, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            self._t.request(
                "PUT", f"/admin/email-templates/{key}", json_body=body
            )
        )

    def reset(self, key: str) -> Dict[str, Any]:
        return _unwrap(
            self._t.request("POST", f"/admin/email-templates/{key}/reset")
        )


class _EmailInbox:
    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request(
            "GET", "/admin/email-inbox", params=params or None
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def send(self, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            self._t.request("POST", "/admin/email-inbox/send", json_body=body)
        )

    def mark_read(self, message_id: str) -> Dict[str, Any]:
        return _unwrap(
            self._t.request("POST", f"/admin/email-inbox/{message_id}/read")
        )

    def archive(self, message_id: str) -> Dict[str, Any]:
        return _unwrap(
            self._t.request("POST", f"/admin/email-inbox/{message_id}/archive")
        )


class Email:
    """Admin email surface with ``campaigns``, ``templates``, ``inbox`` sub-namespaces."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport
        self.campaigns = _EmailCampaigns(transport)
        self.templates = _EmailTemplates(transport)
        self.inbox = _EmailInbox(transport)


# ── Async sub-namespaces ───────────────────────────────────────────────


class _AsyncEmailCampaigns:
    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request(
            "GET", "/admin/email-campaigns", params=params or None
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def create(self, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            await self._t.request(
                "POST", "/admin/email-campaigns", json_body=body
            )
        )

    async def recipient_count(self, **filters: Any) -> Dict[str, Any]:
        params = {k: v for k, v in filters.items() if v is not None}
        return _unwrap(
            await self._t.request(
                "GET",
                "/admin/email-campaigns/recipient-count",
                params=params or None,
            )
        )

    async def send(self, campaign_id: str, **opts: Any) -> Dict[str, Any]:
        body = {k: v for k, v in opts.items() if v is not None}
        return _unwrap(
            await self._t.request(
                "POST",
                f"/admin/email-campaigns/{campaign_id}/send",
                json_body=body,
            )
        )

    async def cancel(self, campaign_id: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST", f"/admin/email-campaigns/{campaign_id}/cancel"
            )
        )

    async def deliveries(
        self, campaign_id: str, **filters: Any
    ) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request(
            "GET",
            f"/admin/email-campaigns/{campaign_id}/deliveries",
            params=params or None,
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []


class _AsyncEmailTemplates:
    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request(
            "GET", "/admin/email-templates", params=params or None
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def create(self, *, key: str, **attrs: Any) -> Dict[str, Any]:
        body = {"key": key, **{k: v for k, v in attrs.items() if v is not None}}
        return _unwrap(
            await self._t.request(
                "POST", "/admin/email-templates", json_body=body
            )
        )

    async def update(self, key: str, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            await self._t.request(
                "PUT", f"/admin/email-templates/{key}", json_body=body
            )
        )

    async def reset(self, key: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST", f"/admin/email-templates/{key}/reset"
            )
        )


class _AsyncEmailInbox:
    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request(
            "GET", "/admin/email-inbox", params=params or None
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def send(self, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            await self._t.request(
                "POST", "/admin/email-inbox/send", json_body=body
            )
        )

    async def mark_read(self, message_id: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST", f"/admin/email-inbox/{message_id}/read"
            )
        )

    async def archive(self, message_id: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST", f"/admin/email-inbox/{message_id}/archive"
            )
        )


class AsyncEmail:
    """Async admin email surface."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport
        self.campaigns = _AsyncEmailCampaigns(transport)
        self.templates = _AsyncEmailTemplates(transport)
        self.inbox = _AsyncEmailInbox(transport)


__all__ = ["Email", "AsyncEmail"]
