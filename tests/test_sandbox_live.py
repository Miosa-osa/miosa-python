"""Credential-gated live E2E coverage for the native Sandbox API."""

from __future__ import annotations

import asyncio
import os
import time
import urllib.request

import pytest

from miosa import AsyncMiosa, Miosa

pytestmark = pytest.mark.skipif(
    not os.environ.get("MIOSA_API_KEY"),
    reason="set MIOSA_API_KEY to run live sandbox E2E tests",
)

BASE_URL = os.environ.get("MIOSA_BASE_URL", "https://api.miosa.ai/api/v1")


def _wait_ready(sandbox, timeout: float = 60.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        sandbox.refresh()
        if sandbox.state == "running" and sandbox.ready:
            return sandbox
        time.sleep(0.5)
    raise AssertionError(f"sandbox {sandbox.id} did not become ready within {timeout}s")


async def _await_ready(sandbox, timeout: float = 60.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        await sandbox.refresh()
        if sandbox.state == "running" and sandbox.ready:
            return sandbox
        await asyncio.sleep(0.5)
    raise AssertionError(f"sandbox {sandbox.id} did not become ready within {timeout}s")


def test_live_sync_sandbox_create_exec_files_preview_destroy():
    marker = f"miosa-py-live-{int(time.time() * 1000)}"
    port = 32174
    client = Miosa(base_url=BASE_URL, timeout=60.0, max_retries=1)
    sandbox = None

    try:
        sandbox = client.sandboxes.create(
            name=f"sdk-py-live-{int(time.time())}",
            template_id="miosa-sandbox",
            timeout_sec=600,
            metadata={"test": "python-live-e2e"},
        )
        _wait_ready(sandbox)

        result = sandbox.commands.run("python3 -c 'print(21 * 2)'", {"timeout": 30})
        assert result.exit_code == 0
        assert result.stdout.strip() == "42"

        sandbox.files.write("/workspace/index.html", f"<h1>{marker}</h1>")
        assert marker in sandbox.files.read_text("/workspace/index.html")
        assert "index.html" in str(sandbox.files.list("/workspace"))
        assert int(sandbox.files.stat("/workspace/index.html").get("size", 0)) > 0

        sandbox.commands.run(
            "cd /workspace && "
            f"nohup python3 -m http.server {port} --bind 0.0.0.0 "
            ">/tmp/miosa-py-live.log 2>&1 &",
            {"timeout": 10},
        )

        reachable = False
        for _ in range(20):
            probe = sandbox.commands.run(
                "python3 - <<'PY'\n"
                "import urllib.request\n"
                f"url = 'http://127.0.0.1:{port}'\n"
                "print(urllib.request.urlopen(url, timeout=2).read().decode())\n"
                "PY",
                {"timeout": 5},
            )
            if probe.exit_code == 0 and marker in probe.stdout:
                reachable = True
                break
            time.sleep(0.5)
        assert reachable

        preview_url = sandbox.preview.expose(port)
        assert preview_url.startswith("https://")
        with urllib.request.urlopen(preview_url, timeout=10) as response:
            assert response.status == 200
            assert marker in response.read().decode("utf-8")
    finally:
        if sandbox is not None:
            try:
                sandbox.destroy()
            finally:
                client.close()
        else:
            client.close()


@pytest.mark.asyncio
async def test_live_async_sandbox_create_exec_files_preview_destroy():
    marker = f"miosa-py-async-live-{int(time.time() * 1000)}"
    port = 32175
    client = AsyncMiosa(base_url=BASE_URL, timeout=60.0, max_retries=1)
    sandbox = None

    try:
        sandbox = await client.sandboxes.create(
            name=f"sdk-py-async-live-{int(time.time())}",
            template_id="miosa-sandbox",
            timeout_sec=600,
            metadata={"test": "python-async-live-e2e"},
        )
        await _await_ready(sandbox)

        result = await sandbox.commands.run("python3 -c 'print(21 * 2)'", {"timeout": 30})
        assert result.exit_code == 0
        assert result.stdout.strip() == "42"

        await sandbox.files.write("/workspace/index.html", f"<h1>{marker}</h1>")
        assert marker in await sandbox.files.read_text("/workspace/index.html")
        assert "index.html" in str(await sandbox.files.list("/workspace"))
        assert int((await sandbox.files.stat("/workspace/index.html")).get("size", 0)) > 0

        await sandbox.commands.run(
            "cd /workspace && "
            f"nohup python3 -m http.server {port} --bind 0.0.0.0 "
            ">/tmp/miosa-py-async-live.log 2>&1 &",
            {"timeout": 10},
        )

        reachable = False
        for _ in range(20):
            probe = await sandbox.commands.run(
                "python3 - <<'PY'\n"
                "import urllib.request\n"
                f"url = 'http://127.0.0.1:{port}'\n"
                "print(urllib.request.urlopen(url, timeout=2).read().decode())\n"
                "PY",
                {"timeout": 5},
            )
            if probe.exit_code == 0 and marker in probe.stdout:
                reachable = True
                break
            await asyncio.sleep(0.5)
        assert reachable

        preview_url = await sandbox.preview.expose(port)
        assert preview_url.startswith("https://")

        def fetch_preview() -> str:
            with urllib.request.urlopen(preview_url, timeout=10) as response:
                assert response.status == 200
                return response.read().decode("utf-8")

        body = await asyncio.to_thread(fetch_preview)
        assert marker in body
    finally:
        if sandbox is not None:
            await sandbox.destroy()
        await client.close()
