"""Tests for the Tokens resource (Layer 2 scoped delegation)."""

from __future__ import annotations

import pytest

from miosa import Miosa
from miosa.resources.tokens import AsyncTokens, Tokens


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

    def test_async_tokens_attribute_exists_on_async_client(self):
        from miosa import AsyncMiosa

        client = AsyncMiosa(api_key="msk_u_test")
        assert hasattr(client, "tokens")
        assert isinstance(client.tokens, AsyncTokens)

    def test_async_create_scoped_raises_on_empty_user_id(self):
        import asyncio
        from miosa import AsyncMiosa

        client = AsyncMiosa(api_key="msk_u_test")

        async def run():
            with pytest.raises(ValueError, match="user_id"):
                await client.tokens.create_scoped(user_id="", workspace_id="ws-1")

        asyncio.run(run())
