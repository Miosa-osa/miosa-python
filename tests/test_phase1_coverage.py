"""Phase-1 SDK coverage tests — tenant.preview_domain, tenant.branding,
sandbox.update, sandbox.preview_token, slug in create, webhooks.verify_signature.
"""

from __future__ import annotations

import hashlib
import hmac
import time

import pytest
import respx
import httpx

from miosa import Miosa
from miosa.resources.webhooks import verify_signature

API_KEY = "msk_u_test_key"
BASE_URL = "https://api.miosa.ai/api/v1"


@pytest.fixture()
def client():
    return Miosa(api_key=API_KEY, base_url=BASE_URL)


# ---------------------------------------------------------------------------
# tenant.preview_domain
# ---------------------------------------------------------------------------

class TestTenantPreviewDomain:
    @respx.mock
    def test_get(self, client: Miosa):
        respx.get(f"{BASE_URL}/tenant/preview-domain").mock(
            return_value=httpx.Response(200, json={"domain": "preview.acme.com", "verified_at": None, "cname_target": "proxy.miosa.app"})
        )
        result = client.tenant.preview_domain.get()
        assert result["domain"] == "preview.acme.com"

    @respx.mock
    def test_set(self, client: Miosa):
        respx.put(f"{BASE_URL}/tenant/preview-domain").mock(
            return_value=httpx.Response(200, json={"domain": "preview.acme.com", "verified_at": None, "cname_target": "proxy.miosa.app"})
        )
        result = client.tenant.preview_domain.set("preview.acme.com")
        assert result["domain"] == "preview.acme.com"

    @respx.mock
    def test_verify(self, client: Miosa):
        respx.post(f"{BASE_URL}/tenant/preview-domain/verify").mock(
            return_value=httpx.Response(200, json={"verified": True, "target": "proxy.miosa.app", "records": []})
        )
        result = client.tenant.preview_domain.verify()
        assert result["verified"] is True

    @respx.mock
    def test_delete(self, client: Miosa):
        respx.delete(f"{BASE_URL}/tenant/preview-domain").mock(
            return_value=httpx.Response(204)
        )
        client.tenant.preview_domain.delete()  # should not raise


# ---------------------------------------------------------------------------
# tenant.branding
# ---------------------------------------------------------------------------

class TestTenantBranding:
    @respx.mock
    def test_get(self, client: Miosa):
        respx.get(f"{BASE_URL}/tenant/branding").mock(
            return_value=httpx.Response(200, json={"product_name": "Acme AI", "logo_url": "https://acme.com/logo.png"})
        )
        result = client.tenant.branding.get()
        assert result["product_name"] == "Acme AI"

    @respx.mock
    def test_set(self, client: Miosa):
        branding = {"product_name": "Acme AI", "primary_color": "#ff0000"}
        respx.put(f"{BASE_URL}/tenant/branding").mock(
            return_value=httpx.Response(200, json=branding)
        )
        result = client.tenant.branding.set(branding)
        assert result["primary_color"] == "#ff0000"

    @respx.mock
    def test_delete(self, client: Miosa):
        respx.delete(f"{BASE_URL}/tenant/branding").mock(
            return_value=httpx.Response(204)
        )
        client.tenant.branding.delete()  # should not raise


# ---------------------------------------------------------------------------
# sandbox.update
# ---------------------------------------------------------------------------

SANDBOX_JSON = {
    "id": "sbx_abc123",
    "tenant_id": "t1",
    "template_id": "miosa-sandbox",
    "state": "running",
    "ready": True,
    "cpu_count": 2,
    "memory_mb": 2048,
    "disk_size_mb": 8192,
    "timeout_sec": 3600,
    "created_at": "2026-05-13T00:00:00Z",
}


class TestSandboxUpdate:
    @respx.mock
    def test_update_name(self, client: Miosa):
        respx.post(f"{BASE_URL}/sandboxes").mock(
            return_value=httpx.Response(200, json={"data": SANDBOX_JSON})
        )
        updated = dict(SANDBOX_JSON)
        updated["name"] = "renamed"
        respx.patch(f"{BASE_URL}/sandboxes/sbx_abc123").mock(
            return_value=httpx.Response(200, json={"data": updated})
        )
        sbx = client.sandboxes.create()
        result = sbx.update(name="renamed")
        assert result.data.get("name") == "renamed"

    @respx.mock
    def test_update_slug_and_tags(self, client: Miosa):
        respx.post(f"{BASE_URL}/sandboxes").mock(
            return_value=httpx.Response(200, json={"data": SANDBOX_JSON})
        )
        updated = dict(SANDBOX_JSON)
        updated["slug"] = "my-slug"
        respx.patch(f"{BASE_URL}/sandboxes/sbx_abc123").mock(
            return_value=httpx.Response(200, json={"data": updated})
        )
        sbx = client.sandboxes.create()
        result = sbx.update(slug="my-slug", tags=["tag1"])
        assert result.data.get("slug") == "my-slug"


# ---------------------------------------------------------------------------
# sandbox.preview_token
# ---------------------------------------------------------------------------

class TestSandboxPreviewToken:
    @respx.mock
    def test_preview_token(self, client: Miosa):
        respx.post(f"{BASE_URL}/sandboxes").mock(
            return_value=httpx.Response(200, json={"data": SANDBOX_JSON})
        )
        token_resp = {"token": "tok_xyz", "url": "https://preview.miosa.app?t=tok_xyz", "expires_at": "2026-05-26T01:00:00Z", "scope": "read"}
        respx.post(f"{BASE_URL}/sandboxes/sbx_abc123/preview-token").mock(
            return_value=httpx.Response(200, json=token_resp)
        )
        sbx = client.sandboxes.create()
        result = sbx.preview_token(expires_in=3600, scope="read")
        assert result["token"] == "tok_xyz"
        assert result["scope"] == "read"


# ---------------------------------------------------------------------------
# sandboxes.create with slug + external_user_id
# ---------------------------------------------------------------------------

class TestSandboxCreateSlug:
    @respx.mock
    def test_create_with_slug_and_external_ids(self, client: Miosa):
        route = respx.post(f"{BASE_URL}/sandboxes").mock(
            return_value=httpx.Response(200, json={"data": SANDBOX_JSON})
        )
        client.sandboxes.create(slug="my-sandbox", external_user_id="usr_1", external_workspace_id="ws_1", external_project_id="proj_1")
        body = route.calls[0].request
        import json
        sent = json.loads(body.content)
        assert sent["slug"] == "my-sandbox"
        assert sent["external_user_id"] == "usr_1"
        assert sent["external_workspace_id"] == "ws_1"


# ---------------------------------------------------------------------------
# webhooks.verify_signature
# ---------------------------------------------------------------------------

class TestVerifySignature:
    def _make_header(self, payload: bytes, secret: str, ts: int | None = None) -> str:
        if ts is None:
            ts = int(time.time())
        signed = f"{ts}.".encode() + payload
        sig = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()  # type: ignore[attr-defined]
        return f"t={ts},v1={sig}"

    def test_valid_signature(self):
        payload = b'{"event":"sandbox.created"}'
        header = self._make_header(payload, "secret123")
        assert verify_signature(payload, header, "secret123") is True

    def test_wrong_secret(self):
        payload = b'{"event":"sandbox.created"}'
        header = self._make_header(payload, "secret123")
        assert verify_signature(payload, header, "wrongsecret") is False

    def test_old_timestamp_raises(self):
        payload = b'{"event":"sandbox.created"}'
        old_ts = int(time.time()) - 400
        header = self._make_header(payload, "secret123", ts=old_ts)
        with pytest.raises(ValueError, match="too old"):
            verify_signature(payload, header, "secret123")

    def test_missing_parts_returns_false(self):
        assert verify_signature(b"body", "malformed", "secret") is False
