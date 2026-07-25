"""Tests for the Tokens resource (Layer 2 scoped delegation)."""

from __future__ import annotations

import asyncio

import pytest

from miosa import Miosa
from miosa.resources.tokens import AsyncTokens, Tokens


class FakeSyncTransport:
    def __init__(self) -> None:
        self.calls = []

    def request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        return {
            "data": {
                "token": "mst_test",
                "expires_at": "2026-06-12T00:00:00Z",
                "scopes": ["sandboxes:create"],
            }
        }


class FakeAsyncTransport:
    def __init__(self) -> None:
        self.calls = []

    async def request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        return {
            "data": {
                "token": "mst_async_test",
                "expires_at": "2026-06-12T00:00:00Z",
                "scopes": ["sandboxes:exec"],
            }
        }


class TestTokensResourceUnit:
    """Unit tests that do not require a live server."""

    def test_tokens_attribute_exists_on_client(self):
        client = Miosa(api_key="msk_u_test")
        assert hasattr(client, "tokens")
        assert isinstance(client.tokens, Tokens)
        client.close()

    def test_create_scoped_raises_on_empty_user_id(self):
        client = Miosa(api_key="msk_u_test")
        with pytest.raises(ValueError, match="user_id"):
            client.tokens.create_scoped(user_id="", workspace_id="ws-1")
        client.close()

    def test_create_scoped_raises_on_empty_workspace_id(self):
        client = Miosa(api_key="msk_u_test")
        with pytest.raises(ValueError, match="workspace_id"):
            client.tokens.create_scoped(user_id="u1", workspace_id="")
        client.close()

    def test_create_scoped_method_exists(self):
        assert callable(getattr(Tokens, "create_scoped", None))

    def test_create_scoped_uses_transport_json_body_and_unwraps_response(self):
        transport = FakeSyncTransport()
        tokens = Tokens(transport)

        result = tokens.create_scoped(
            user_id="cliniciq-user-1",
            workspace_id="workspace-1",
            expires_in_seconds=900,
            scopes=["sandboxes:create"],
            external_project_id="project-1",
            ignored_none=None,
        )

        assert result["token"] == "mst_test"
        assert transport.calls == [
            (
                "POST",
                "/tokens/scoped",
                {
                    "json_body": {
                        "user_id": "cliniciq-user-1",
                        "workspace_id": "workspace-1",
                        "expires_in_seconds": 900,
                        "scopes": ["sandboxes:create"],
                        "external_project_id": "project-1",
                    }
                },
            )
        ]

    def test_async_tokens_attribute_exists_on_async_client(self):
        from miosa import AsyncMiosa

        client = AsyncMiosa(api_key="msk_u_test")
        assert hasattr(client, "tokens")
        assert isinstance(client.tokens, AsyncTokens)

    def test_async_create_scoped_raises_on_empty_user_id(self):
        from miosa import AsyncMiosa

        client = AsyncMiosa(api_key="msk_u_test")

        async def run():
            with pytest.raises(ValueError, match="user_id"):
                await client.tokens.create_scoped(user_id="", workspace_id="ws-1")

        asyncio.run(run())

    @pytest.mark.asyncio
    async def test_async_create_scoped_uses_transport_json_body_and_unwraps_response(self):
        transport = FakeAsyncTransport()
        tokens = AsyncTokens(transport)

        result = await tokens.create_scoped(
            user_id="cliniciq-user-1",
            workspace_id="workspace-1",
            expires_in_seconds=900,
            scopes=["sandboxes:exec"],
        )

        assert result["token"] == "mst_async_test"
        assert transport.calls == [
            (
                "POST",
                "/tokens/scoped",
                {
                    "json_body": {
                        "user_id": "cliniciq-user-1",
                        "workspace_id": "workspace-1",
                        "expires_in_seconds": 900,
                        "scopes": ["sandboxes:exec"],
                    }
                },
            )
        ]
