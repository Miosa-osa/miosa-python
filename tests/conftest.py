"""Shared test fixtures for the MIOSA Python SDK."""

from __future__ import annotations

import pytest
import respx

from miosa import AsyncMiosa, Miosa

API_KEY = "msk_u_test_key_12345"
BASE_URL = "https://api.miosa.ai/api/v1"


COMPUTER_JSON = {
    "id": "comp_abc123",
    "name": "test-agent",
    "slug": "test-agent",
    "status": "running",
    "template_type": "miosa-desktop",
    "size": "small",
    "ip_address": "10.0.0.5",
    "created_at": "2026-04-01T00:00:00Z",
    "updated_at": "2026-04-01T00:00:00Z",
    "metadata": None,
}


SANDBOX_JSON = {
    "id": "sbx_abc123",
    "tenant_id": "tenant_123",
    "owner_id": "user_123",
    "template_id": "miosa-sandbox",
    "image_id": "debian-12-sandbox-v8",
    "state": "running",
    "ready": True,
    "cpu_count": 2,
    "memory_mb": 2048,
    "disk_size_mb": 8192,
    "timeout_sec": 3600,
    "total_runtime_sec": None,
    "metadata": {"project": "demo"},
    "created_at": "2026-05-13T00:00:00Z",
    "started_at": "2026-05-13T00:00:01Z",
    "ready_at": "2026-05-13T00:00:01Z",
    "destroyed_at": None,
    "preview_url": "https://3000-sbxabc.sandbox.miosa.ai",
    "boot_path": "snapshot",
    "boot_ms": 166,
}


@pytest.fixture
def mock_api():
    """respx mock router scoped to the MIOSA base URL."""
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        yield router


@pytest.fixture
def client():
    """Synchronous Miosa client with retry disabled for fast tests."""
    c = Miosa(api_key=API_KEY, base_url=BASE_URL, max_retries=0)
    yield c
    c.close()


@pytest.fixture
def async_client():
    """Asynchronous Miosa client with retry disabled for fast tests."""
    return AsyncMiosa(api_key=API_KEY, base_url=BASE_URL, max_retries=0)
