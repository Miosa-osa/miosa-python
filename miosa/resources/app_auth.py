"""AppAuth — end-user authentication client for apps deployed on MIOSA.

AUTH_URL and AUTH_JWT_SECRET are injected automatically when a sandbox or
deployment boots. Instantiate AppAuth (or AsyncAppAuth) inside your app and
call signup/login/verify/logout/me. Call verify_token() server-side to
validate incoming JWTs without a network round-trip.

Example::

    from miosa.resources.app_auth import AppAuth

    auth = AppAuth(resource_type="deployment", resource_id="dep_abc")

    session = auth.signup("alice@example.com", "hunter2")
    print(session["userId"], session["token"])

    payload = auth.verify_token(session["token"])
    print(payload["sub"])
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

# ── Types ─────────────────────────────────────────────────────────────────────

# These are plain TypedDict-style aliases kept as Dict for Python 3.9 compat.
# The keys mirror the camelCase surface the TypeScript SDK exposes.
AppAuthSession = Dict[str, Any]
"""Dict with keys: userId, token, expiresAt."""

AppAuthTokenPayload = Dict[str, Any]
"""Decoded JWT payload dict."""


# ── Helpers ───────────────────────────────────────────────────────────────────


def _unwrap_session(data: Any) -> AppAuthSession:
    d: Dict[str, Any] = data.get("data", data) if isinstance(data, dict) else data
    user_id = d.get("user_id") or d.get("userId")
    token = d.get("token") or d.get("access_token")
    expires_at = d.get("expires_at") or d.get("expiresAt") or ""
    if not user_id or not token:
        raise ValueError(
            f"AppAuth: unexpected response shape — got: {d!r}"
        )
    return {"userId": user_id, "token": token, "expiresAt": expires_at}


def _base64url_decode(s: str) -> bytes:
    padded = s.replace("-", "+").replace("_", "/")
    padding = 4 - len(padded) % 4
    if padding != 4:
        padded += "=" * padding
    return base64.b64decode(padded)


def _verify_hs256(token: str, secret: str) -> AppAuthTokenPayload:
    """Verify an HS256 JWT locally. Raises ValueError on failure."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("AppAuth.verify_token: malformed JWT — expected 3 parts")
    header_b64, payload_b64, sig_b64 = parts

    # Decode payload to check expiry before crypto work.
    payload: AppAuthTokenPayload = json.loads(_base64url_decode(payload_b64))
    exp = payload.get("exp")
    if isinstance(exp, (int, float)) and exp < time.time():
        raise ValueError(
            f"AppAuth.verify_token: token expired at"
            f" {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(exp))}"
        )

    # HS256 signature verification.
    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected_sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    actual_sig = _base64url_decode(sig_b64)
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("AppAuth.verify_token: invalid JWT signature")

    return payload


# ── Sync client ───────────────────────────────────────────────────────────────


class AppAuth:
    """Synchronous AppAuth client.

    Reads AUTH_URL from env by default (injected at sandbox/deployment boot).
    Pass auth_url explicitly to override.
    """

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        *,
        auth_url: Optional[str] = None,
        jwt_secret: Optional[str] = None,
    ) -> None:
        resolved_url = auth_url or os.environ.get("AUTH_URL")
        if not resolved_url:
            raise ValueError(
                "AppAuth: auth_url is required."
                " Pass auth_url= or set the AUTH_URL environment variable."
            )
        if not resource_type or not resource_id:
            raise ValueError("AppAuth: resource_type and resource_id are required.")
        self._base_url = resolved_url.rstrip("/")
        self._resource_type = resource_type
        self._resource_id = resource_id
        self._jwt_secret = jwt_secret or os.environ.get("AUTH_JWT_SECRET")

    # ── Public methods ────────────────────────────────────────────────────────

    def signup(self, email: str, password: str) -> AppAuthSession:
        """POST /app-auth/:resource_type/:resource_id/signup"""
        return _unwrap_session(self._post("signup", {"email": email, "password": password}))

    def login(self, email: str, password: str) -> AppAuthSession:
        """POST /app-auth/:resource_type/:resource_id/login"""
        return _unwrap_session(self._post("login", {"email": email, "password": password}))

    def verify(self, token: str) -> AppAuthSession:
        """POST /app-auth/:resource_type/:resource_id/verify — confirm email/magic-link."""
        return _unwrap_session(self._post("verify", {"token": token}))

    def password_reset(self, email: str) -> Dict[str, Any]:
        """POST /app-auth/:resource_type/:resource_id/password-reset"""
        data = self._post("password-reset", {"email": email})
        return {"ok": True, **(data if isinstance(data, dict) else {})}

    def logout(self, token: str) -> Dict[str, Any]:
        """POST /app-auth/:resource_type/:resource_id/logout — invalidates token server-side."""
        data = self._post("logout", {"token": token})
        return {"ok": True, **(data if isinstance(data, dict) else {})}

    def me(self, token: str) -> AppAuthSession:
        """GET /app-auth/:resource_type/:resource_id/me — fetch session for bearer token."""
        import httpx  # lazy import; httpx is a required dep of the SDK

        url = self._action_url("me")
        resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"})
        if resp.is_error:
            raise RuntimeError(
                f"AppAuth me failed ({resp.status_code}): {resp.text}"
            )
        return _unwrap_session(resp.json())

    def verify_token(self, token: str) -> AppAuthTokenPayload:
        """Verify a JWT locally using HS256 + AUTH_JWT_SECRET (no network call).

        Raises ValueError if the token is expired, has an invalid signature,
        or jwt_secret is not configured.
        """
        if not self._jwt_secret:
            raise ValueError(
                "AppAuth.verify_token: jwt_secret is required."
                " Pass jwt_secret= or set the AUTH_JWT_SECRET environment variable."
            )
        return _verify_hs256(token, self._jwt_secret)

    # ── Private ───────────────────────────────────────────────────────────────

    def _action_url(self, action: str) -> str:
        return (
            f"{self._base_url}/app-auth"
            f"/{self._resource_type}/{self._resource_id}/{action}"
        )

    def _post(self, action: str, body: Dict[str, Any]) -> Any:
        import httpx

        resp = httpx.post(self._action_url(action), json=body)
        if resp.is_error:
            raise RuntimeError(
                f"AppAuth {action} failed ({resp.status_code}): {resp.text}"
            )
        return resp.json()


# ── Async client ──────────────────────────────────────────────────────────────


class AsyncAppAuth:
    """Asynchronous AppAuth client (mirrors AppAuth exactly with async/await)."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        *,
        auth_url: Optional[str] = None,
        jwt_secret: Optional[str] = None,
    ) -> None:
        resolved_url = auth_url or os.environ.get("AUTH_URL")
        if not resolved_url:
            raise ValueError(
                "AsyncAppAuth: auth_url is required."
                " Pass auth_url= or set the AUTH_URL environment variable."
            )
        if not resource_type or not resource_id:
            raise ValueError(
                "AsyncAppAuth: resource_type and resource_id are required."
            )
        self._base_url = resolved_url.rstrip("/")
        self._resource_type = resource_type
        self._resource_id = resource_id
        self._jwt_secret = jwt_secret or os.environ.get("AUTH_JWT_SECRET")

    # ── Public methods ────────────────────────────────────────────────────────

    async def signup(self, email: str, password: str) -> AppAuthSession:
        """POST /app-auth/:resource_type/:resource_id/signup"""
        return _unwrap_session(
            await self._post("signup", {"email": email, "password": password})
        )

    async def login(self, email: str, password: str) -> AppAuthSession:
        """POST /app-auth/:resource_type/:resource_id/login"""
        return _unwrap_session(
            await self._post("login", {"email": email, "password": password})
        )

    async def verify(self, token: str) -> AppAuthSession:
        """POST /app-auth/:resource_type/:resource_id/verify"""
        return _unwrap_session(await self._post("verify", {"token": token}))

    async def password_reset(self, email: str) -> Dict[str, Any]:
        """POST /app-auth/:resource_type/:resource_id/password-reset"""
        data = await self._post("password-reset", {"email": email})
        return {"ok": True, **(data if isinstance(data, dict) else {})}

    async def logout(self, token: str) -> Dict[str, Any]:
        """POST /app-auth/:resource_type/:resource_id/logout"""
        data = await self._post("logout", {"token": token})
        return {"ok": True, **(data if isinstance(data, dict) else {})}

    async def me(self, token: str) -> AppAuthSession:
        """GET /app-auth/:resource_type/:resource_id/me"""
        import httpx

        url = self._action_url("me")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url, headers={"Authorization": f"Bearer {token}"}
            )
        if resp.is_error:
            raise RuntimeError(
                f"AsyncAppAuth me failed ({resp.status_code}): {resp.text}"
            )
        return _unwrap_session(resp.json())

    def verify_token(self, token: str) -> AppAuthTokenPayload:
        """Verify JWT locally (synchronous — no I/O involved)."""
        if not self._jwt_secret:
            raise ValueError(
                "AsyncAppAuth.verify_token: jwt_secret is required."
                " Pass jwt_secret= or set the AUTH_JWT_SECRET environment variable."
            )
        return _verify_hs256(token, self._jwt_secret)

    # ── Private ───────────────────────────────────────────────────────────────

    def _action_url(self, action: str) -> str:
        return (
            f"{self._base_url}/app-auth"
            f"/{self._resource_type}/{self._resource_id}/{action}"
        )

    async def _post(self, action: str, body: Dict[str, Any]) -> Any:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(self._action_url(action), json=body)
        if resp.is_error:
            raise RuntimeError(
                f"AsyncAppAuth {action} failed ({resp.status_code}): {resp.text}"
            )
        return resp.json()
