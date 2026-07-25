"""
AppAuth usage example — sync and async.

AUTH_URL and AUTH_JWT_SECRET are injected automatically when your app boots
inside a MIOSA sandbox or deployment. Run locally by exporting them:

    export AUTH_URL=https://your-app.miosa.app
    export AUTH_JWT_SECRET=your-secret
    export RESOURCE_ID=dep_demo
    uv run python examples/app_auth_example.py
"""

from __future__ import annotations

import os

from miosa.resources.app_auth import AppAuth, AsyncAppAuth


def sync_example() -> None:
    auth = AppAuth(
        resource_type="deployment",
        resource_id=os.environ.get("RESOURCE_ID", "dep_demo"),
        # auth_url and jwt_secret read from AUTH_URL / AUTH_JWT_SECRET env vars
    )

    # Sign up
    session = auth.signup("alice@example.com", "hunter2")
    print("Signed up:", session["userId"], "token:", session["token"])

    # Login
    login_session = auth.login("alice@example.com", "hunter2")
    print("Logged in, expires:", login_session["expiresAt"])

    # Verify token locally (no network call)
    payload = auth.verify_token(login_session["token"])
    print("Token sub:", payload["sub"])

    # Password reset
    auth.password_reset("alice@example.com")
    print("Password reset email sent")

    # Logout
    auth.logout(login_session["token"])
    print("Logged out")


async def async_example() -> None:
    import asyncio

    auth = AsyncAppAuth(
        resource_type="deployment",
        resource_id=os.environ.get("RESOURCE_ID", "dep_demo"),
    )

    session = await auth.signup("bob@example.com", "s3cr3t")
    print("Async signed up:", session["userId"])

    payload = auth.verify_token(session["token"])
    print("Async token sub:", payload["sub"])

    await auth.logout(session["token"])
    print("Async logged out")


if __name__ == "__main__":
    import asyncio

    sync_example()
    asyncio.run(async_example())
