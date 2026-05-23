"""OpenComputers Terminal and Desktop ticket resources — sync and async."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .types import WsTicket

if TYPE_CHECKING:
    from ..._http import AsyncTransport, SyncTransport


class TerminalResource:
    """Issue WebSocket tickets for PTY sessions on a remote host (sync)."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def ticket(self, host_id: str) -> WsTicket:
        """Issue a short-lived WebSocket ticket for an interactive terminal."""
        data = self._transport.request(
            "POST", f"/opencomputers/hosts/{host_id}/terminal/ticket"
        )
        return WsTicket.model_validate(data)


class AsyncTerminalResource:
    """Issue WebSocket tickets for PTY sessions on a remote host (async)."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def ticket(self, host_id: str) -> WsTicket:
        data = await self._transport.request(
            "POST", f"/opencomputers/hosts/{host_id}/terminal/ticket"
        )
        return WsTicket.model_validate(data)


class DesktopResource:
    """Issue WebSocket tickets for KasmVNC desktop streaming (sync)."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def ticket(self, host_id: str) -> WsTicket:
        """Issue a short-lived WebSocket ticket for desktop streaming."""
        data = self._transport.request(
            "POST", f"/opencomputers/hosts/{host_id}/desktop/ticket"
        )
        return WsTicket.model_validate(data)


class AsyncDesktopResource:
    """Issue WebSocket tickets for KasmVNC desktop streaming (async)."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def ticket(self, host_id: str) -> WsTicket:
        data = await self._transport.request(
            "POST", f"/opencomputers/hosts/{host_id}/desktop/ticket"
        )
        return WsTicket.model_validate(data)
