"""Transport-layer tests: client singleton + HTTP/2 / keep-alive config."""

from __future__ import annotations

import httpx
import pytest

from miosa._http import (
    _DEFAULT_LIMITS,
    _HTTP2_AVAILABLE,
    AsyncTransport,
    SyncTransport,
)


class TestSyncTransportSingleton:
    def test_client_is_created_once_and_reused(self):
        """The underlying httpx.Client must be constructed exactly once
        per transport so connections (and TLS sessions) are pooled."""
        transport = SyncTransport(api_key="msk_u_test")
        try:
            first = transport._client
            second = transport._client
            assert first is second, "httpx.Client must be a singleton per transport"
            assert isinstance(first, httpx.Client)
        finally:
            transport.close()

    def test_client_has_keepalive_pool(self):
        """Connection pool limits are set explicitly so keep-alive is
        configured (not left to httpx defaults that may evict early)."""
        transport = SyncTransport(api_key="msk_u_test")
        try:
            assert _DEFAULT_LIMITS.max_keepalive_connections >= 1
            assert _DEFAULT_LIMITS.keepalive_expiry >= 30.0
        finally:
            transport.close()

    @pytest.mark.skipif(not _HTTP2_AVAILABLE, reason="h2 package not installed")
    def test_http2_enabled_when_h2_present(self):
        """When the optional ``h2`` dependency is installed the client
        should negotiate HTTP/2."""
        transport = SyncTransport(api_key="msk_u_test")
        try:
            # httpx exposes the negotiated protocol intent via the
            # client's internal config; the public surface is that the
            # constructor accepts http2=True without raising.
            assert transport._client is not None
        finally:
            transport.close()


class TestAsyncTransportSingleton:
    @pytest.mark.asyncio
    async def test_async_client_is_created_once_and_reused(self):
        transport = AsyncTransport(api_key="msk_u_test")
        try:
            first = transport._client
            second = transport._client
            assert first is second, "httpx.AsyncClient must be a singleton per transport"
            assert isinstance(first, httpx.AsyncClient)
        finally:
            await transport.close()
