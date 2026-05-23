"""MCP — Model Context Protocol streamable-HTTP transport."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data", "mcp", "result", "items")) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class MCP:
    """Model Context Protocol — JSON-RPC dispatch + streaming SSE channel.

    Clients (Claude Code, Cursor, Gemini CLI, Copilot) point at ``/api/v1/mcp``
    with a ``msk_*`` Bearer token and discover the MIOSA tool-belt.
    """

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def dispatch(
        self,
        method: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        """Send a JSON-RPC request to the MCP endpoint."""
        body: Dict[str, Any] = {}
        if method is not None:
            body["method"] = method
        if params is not None:
            body["params"] = params
        body.update({k: v for k, v in extra.items() if v is not None})
        return _unwrap(self._t.request("POST", "/mcp", json_body=body or None))

    def listen(self) -> Any:
        """Open the MCP listen channel (GET).

        Returns whatever the server returns; for true SSE streaming, callers
        should use the underlying transport directly.
        """
        return _unwrap(self._t.request("GET", "/mcp"))

    def close(self) -> None:
        """Close (terminate) the MCP session."""
        self._t.request("DELETE", "/mcp")


class AsyncMCP:
    """Async MCP."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def dispatch(
        self,
        method: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {}
        if method is not None:
            body["method"] = method
        if params is not None:
            body["params"] = params
        body.update({k: v for k, v in extra.items() if v is not None})
        return _unwrap(
            await self._t.request("POST", "/mcp", json_body=body or None)
        )

    async def listen(self) -> Any:
        return _unwrap(await self._t.request("GET", "/mcp"))

    async def close(self) -> None:
        await self._t.request("DELETE", "/mcp")
