"""External keys — BYOK encrypted per-user provider keys."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(
    data: Any,
    keys: tuple[str, ...] = ("data", "external_keys", "items"),
) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class ExternalKeys:
    """External BYOK keys — Anthropic, OpenAI, Google, Groq, etc.

    Stored encrypted per-user and used by dashboard features (Builder, etc.).
    """

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self) -> List[Dict[str, Any]]:
        """List configured external keys."""
        data = self._t.request("GET", "/external-keys")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def create(self, provider: str, key: str, **attrs: Any) -> Dict[str, Any]:
        """Create / register an external provider key."""
        body = {
            "provider": provider,
            "key": key,
            **{k: v for k, v in attrs.items() if v is not None},
        }
        return _unwrap(self._t.request("POST", "/external-keys", json_body=body))

    def resolve(self, provider: str) -> Dict[str, Any]:
        """Resolve (preview) the stored key for a provider."""
        return _unwrap(
            self._t.request("GET", f"/external-keys/{provider}/resolve")
        )

    def delete(self, provider: str) -> None:
        """Delete the stored key for a provider.

        The backend keys external keys by ``provider`` (not by id).
        """
        self._t.request("DELETE", f"/external-keys/{provider}")


class AsyncExternalKeys:
    """Async external keys."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", "/external-keys")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def create(
        self, provider: str, key: str, **attrs: Any
    ) -> Dict[str, Any]:
        body = {
            "provider": provider,
            "key": key,
            **{k: v for k, v in attrs.items() if v is not None},
        }
        return _unwrap(
            await self._t.request("POST", "/external-keys", json_body=body)
        )

    async def resolve(self, provider: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request("GET", f"/external-keys/{provider}/resolve")
        )

    async def delete(self, provider: str) -> None:
        await self._t.request("DELETE", f"/external-keys/{provider}")
