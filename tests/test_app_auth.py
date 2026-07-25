"""Tests for AppAuth and AsyncAppAuth resources."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict

import pytest

from miosa.resources.app_auth import AppAuth, AsyncAppAuth

# ── Fixtures ──────────────────────────────────────────────────────────────────

AUTH_URL = "https://auth.example.com"
RESOURCE_TYPE = "deployment"
RESOURCE_ID = "dep_abc123"
JWT_SECRET = "super-secret-key-for-tests"

SESSION_RESPONSE = {
    "data": {
        "user_id": "usr_001",
        "token": "tok_abc",
        "expires_at": "2099-01-01T00:00:00Z",
    }
}


def make_auth(**kw: Any) -> AppAuth:
    defaults = dict(
        resource_type=RESOURCE_TYPE,
        resource_id=RESOURCE_ID,
        auth_url=AUTH_URL,
        jwt_secret=JWT_SECRET,
    )
    defaults.update(kw)
    return AppAuth(**defaults)


def make_async_auth(**kw: Any) -> AsyncAppAuth:
    defaults = dict(
        resource_type=RESOURCE_TYPE,
        resource_id=RESOURCE_ID,
        auth_url=AUTH_URL,
        jwt_secret=JWT_SECRET,
    )
    defaults.update(kw)
    return AsyncAppAuth(**defaults)


# ── JWT helpers ───────────────────────────────────────────────────────────────


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def sign_hs256(payload: Dict[str, Any], secret: str) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64url(json.dumps(payload).encode())
    signing_input = f"{header}.{body}".encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url(sig)}"


# ── Fake transports ───────────────────────────────────────────────────────────


class FakeHTTPResponse:
    def __init__(self, data: Any, status_code: int = 200) -> None:
        self._data = data
        self.status_code = status_code
        self.text = json.dumps(data)
        self.is_error = status_code >= 400

    def json(self) -> Any:
        return self._data


# ── Construction tests ────────────────────────────────────────────────────────


class TestAppAuthConstruction:
    def test_raises_when_auth_url_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AUTH_URL", raising=False)
        with pytest.raises(ValueError, match="auth_url is required"):
            AppAuth(resource_type="sandbox", resource_id="sb_1")

    def test_raises_when_resource_type_empty(self) -> None:
        with pytest.raises(ValueError, match="resource_type and resource_id"):
            AppAuth(resource_type="", resource_id="sb_1", auth_url=AUTH_URL)

    def test_raises_when_resource_id_empty(self) -> None:
        with pytest.raises(ValueError, match="resource_type and resource_id"):
            AppAuth(resource_type="sandbox", resource_id="", auth_url=AUTH_URL)

    def test_reads_auth_url_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AUTH_URL", "https://env-auth.example.com")
        # Should not raise
        AppAuth(resource_type="sandbox", resource_id="sb_1")

    def test_async_raises_when_auth_url_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("AUTH_URL", raising=False)
        with pytest.raises(ValueError, match="auth_url is required"):
            AsyncAppAuth(resource_type="sandbox", resource_id="sb_1")


# ── Sync method tests (mock httpx via monkeypatching _post / me) ──────────────


class TestAppAuthSync:
    def test_signup_calls_correct_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[tuple[str, dict[str, Any]]] = []

        def fake_post(self_inner: AppAuth, action: str, body: Dict[str, Any]) -> Any:
            calls.append((action, body))
            return SESSION_RESPONSE

        monkeypatch.setattr(AppAuth, "_post", fake_post)
        auth = make_auth()
        session = auth.signup("alice@example.com", "hunter2")

        assert calls == [("signup", {"email": "alice@example.com", "password": "hunter2"})]
        assert session["userId"] == "usr_001"
        assert session["token"] == "tok_abc"
        assert session["expiresAt"] == "2099-01-01T00:00:00Z"

    def test_login_calls_correct_action(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[tuple[str, dict[str, Any]]] = []

        def fake_post(self_inner: AppAuth, action: str, body: Dict[str, Any]) -> Any:
            calls.append((action, body))
            return SESSION_RESPONSE

        monkeypatch.setattr(AppAuth, "_post", fake_post)
        auth = make_auth()
        session = auth.login("bob@example.com", "secret")

        assert calls[0][0] == "login"
        assert session["userId"] == "usr_001"

    def test_verify_sends_token_body(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[tuple[str, dict[str, Any]]] = []

        def fake_post(self_inner: AppAuth, action: str, body: Dict[str, Any]) -> Any:
            calls.append((action, body))
            return SESSION_RESPONSE

        monkeypatch.setattr(AppAuth, "_post", fake_post)
        make_auth().verify("confirm_tok_xyz")

        assert calls == [("verify", {"token": "confirm_tok_xyz"})]

    def test_logout_sends_token_body(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[tuple[str, dict[str, Any]]] = []

        def fake_post(self_inner: AppAuth, action: str, body: Dict[str, Any]) -> Any:
            calls.append((action, body))
            return {"ok": True}

        monkeypatch.setattr(AppAuth, "_post", fake_post)
        result = make_auth().logout("tok_abc")

        assert calls == [("logout", {"token": "tok_abc"})]
        assert result["ok"] is True

    def test_password_reset_sends_email(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[tuple[str, dict[str, Any]]] = []

        def fake_post(self_inner: AppAuth, action: str, body: Dict[str, Any]) -> Any:
            calls.append((action, body))
            return {}

        monkeypatch.setattr(AppAuth, "_post", fake_post)
        result = make_auth().password_reset("alice@example.com")

        assert calls == [("password-reset", {"email": "alice@example.com"})]
        assert result["ok"] is True

    def test_action_url_format(self) -> None:
        auth = make_auth()
        expected = f"{AUTH_URL}/app-auth/{RESOURCE_TYPE}/{RESOURCE_ID}/signup"
        assert auth._action_url("signup") == expected


# ── verify_token (HS256) ──────────────────────────────────────────────────────


class TestVerifyToken:
    def test_valid_token_returns_payload(self) -> None:
        now = int(time.time())
        token = sign_hs256({"sub": "usr_001", "iat": now, "exp": now + 3600}, JWT_SECRET)
        payload = make_auth().verify_token(token)
        assert payload["sub"] == "usr_001"

    def test_expired_token_raises(self) -> None:
        past = int(time.time()) - 10
        token = sign_hs256({"sub": "usr_001", "iat": past - 3600, "exp": past}, JWT_SECRET)
        with pytest.raises(ValueError, match="expired"):
            make_auth().verify_token(token)

    def test_wrong_secret_raises(self) -> None:
        now = int(time.time())
        token = sign_hs256({"sub": "usr_001", "iat": now, "exp": now + 3600}, "wrong-secret")
        with pytest.raises(ValueError, match="invalid JWT signature"):
            make_auth().verify_token(token)

    def test_malformed_token_raises(self) -> None:
        with pytest.raises(ValueError, match="malformed"):
            make_auth().verify_token("not.a.valid.token")

    def test_raises_when_jwt_secret_not_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)
        auth = AppAuth(
            resource_type=RESOURCE_TYPE,
            resource_id=RESOURCE_ID,
            auth_url=AUTH_URL,
            # jwt_secret intentionally omitted
        )
        with pytest.raises(ValueError, match="jwt_secret"):
            auth.verify_token("a.b.c")


# ── Async client tests ────────────────────────────────────────────────────────


class TestAsyncAppAuth:
    def test_signup_calls_correct_action(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[tuple[str, dict[str, Any]]] = []

        async def fake_post(
            self_inner: AsyncAppAuth, action: str, body: Dict[str, Any]
        ) -> Any:
            calls.append((action, body))
            return SESSION_RESPONSE

        monkeypatch.setattr(AsyncAppAuth, "_post", fake_post)

        auth = make_async_auth()

        async def run() -> None:
            session = await auth.signup("alice@example.com", "hunter2")
            assert session["userId"] == "usr_001"
            assert calls[0] == ("signup", {"email": "alice@example.com", "password": "hunter2"})

        asyncio.run(run())

    def test_login_calls_correct_action(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def fake_post(
            self_inner: AsyncAppAuth, action: str, body: Dict[str, Any]
        ) -> Any:
            return SESSION_RESPONSE

        monkeypatch.setattr(AsyncAppAuth, "_post", fake_post)

        async def run() -> None:
            session = await make_async_auth().login("bob@example.com", "secret")
            assert session["token"] == "tok_abc"

        asyncio.run(run())

    def test_verify_token_sync_on_async_client(self) -> None:
        now = int(time.time())
        token = sign_hs256({"sub": "usr_async", "iat": now, "exp": now + 3600}, JWT_SECRET)
        payload = make_async_auth().verify_token(token)
        assert payload["sub"] == "usr_async"

    def test_logout_returns_ok(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def fake_post(
            self_inner: AsyncAppAuth, action: str, body: Dict[str, Any]
        ) -> Any:
            return {}

        monkeypatch.setattr(AsyncAppAuth, "_post", fake_post)

        async def run() -> None:
            result = await make_async_auth().logout("tok_abc")
            assert result["ok"] is True

        asyncio.run(run())

    def test_password_reset_returns_ok(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def fake_post(
            self_inner: AsyncAppAuth, action: str, body: Dict[str, Any]
        ) -> Any:
            return {}

        monkeypatch.setattr(AsyncAppAuth, "_post", fake_post)

        async def run() -> None:
            result = await make_async_auth().password_reset("alice@example.com")
            assert result["ok"] is True

        asyncio.run(run())
