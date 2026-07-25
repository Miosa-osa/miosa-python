"""Tests for external provider key management."""

from __future__ import annotations

import json

import pytest


def test_create_sends_canonical_value_field(mock_api, client) -> None:
    route = mock_api.post("/external-keys").respond(
        201,
        json={"data": {"provider": "anthropic", "configured": True}},
    )

    result = client.external_keys.create("anthropic", "sk-ant-test")

    body = json.loads(route.calls.last.request.content)
    assert body == {"provider": "anthropic", "value": "sk-ant-test"}
    assert "key" not in body
    assert result["configured"] is True


@pytest.mark.asyncio
async def test_async_create_sends_canonical_value_field(mock_api, async_client) -> None:
    route = mock_api.post("/external-keys").respond(
        201,
        json={"data": {"provider": "openai", "configured": True}},
    )

    result = await async_client.external_keys.create("openai", "sk-openai-test")

    body = json.loads(route.calls.last.request.content)
    assert body == {"provider": "openai", "value": "sk-openai-test"}
    assert "key" not in body
    assert result["configured"] is True
    await async_client.close()
