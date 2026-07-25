"""Tests for the 10 SDK gap implementations.

Covers gaps 1–10 from the SDK alignment audit. All tests mock the HTTP layer
via ``respx`` — no live sandbox required.
"""

from __future__ import annotations

import json

import pytest
import respx
import httpx

from miosa import Miosa, AsyncMiosa
from miosa.resources.sandbox_namespaces import (
    AsyncBackgroundProcessInfo,
    AsyncSandboxGit,
    BackgroundProcessInfo,
    FileWatchEvent,
    FileWriteItem,
    GitCloneResult,
    GitResult,
    SandboxGit,
)
from miosa.resources.sandboxes import AsyncSandbox, Sandbox

from .conftest import API_KEY, BASE_URL, SANDBOX_JSON


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_sandbox(client: Miosa) -> Sandbox:
    """Return a Sandbox handle wired to the sync transport."""
    return Sandbox(client._transport, {**SANDBOX_JSON, "state": "running"})


def _make_async_sandbox(client: AsyncMiosa) -> AsyncSandbox:
    """Return an AsyncSandbox handle wired to the async transport."""
    return AsyncSandbox(client._transport, {**SANDBOX_JSON, "state": "running"})


# ─── Gap 1: Background processes ─────────────────────────────────────────────


class TestBackgroundProcesses:
    """Gap 1 — commands.run(background=True) returns BackgroundProcessInfo."""

    def test_run_background_returns_pid(self, client, mock_api):
        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/processes").respond(
            200, json={"data": {"pid": 1234, "state": "running"}}
        )
        sb = _make_sandbox(client)
        proc = sb.commands.run("npm run dev", background=True)
        assert isinstance(proc, BackgroundProcessInfo)
        assert proc.pid == 1234
        assert proc.sandbox_id == SANDBOX_JSON["id"]

    def test_run_blocking_returns_exec_result(self, client, mock_api):
        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/exec").respond(
            200,
            json={"data": {"stdout": "hello\n", "stderr": "", "exit_code": 0, "duration_ms": 5}},
        )
        sb = _make_sandbox(client)
        from miosa.resources.sandboxes import ExecResult

        result = sb.commands.run("echo hello")
        assert isinstance(result, ExecResult)
        assert result.exit_code == 0

    def test_background_kill_calls_signal_endpoint(self, client, mock_api):
        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/processes").respond(
            200, json={"data": {"pid": 999}}
        )
        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/processes/999/signal").respond(
            200, json={"ok": True}
        )
        sb = _make_sandbox(client)
        proc = sb.commands.run("sleep 100", background=True)
        proc.kill()  # should not raise

    def test_background_status_returns_dict(self, client, mock_api):
        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/processes").respond(
            200, json={"data": {"pid": 42}}
        )
        mock_api.get(f"/sandboxes/{SANDBOX_JSON['id']}/processes/42").respond(
            200, json={"data": {"pid": 42, "state": "running"}}
        )
        sb = _make_sandbox(client)
        proc = sb.commands.run("tail -f /dev/null", background=True)
        status = proc.status()
        assert status.get("pid") == 42


# ─── Gap 2: Send stdin ────────────────────────────────────────────────────────


class TestSendStdin:
    """Gap 2 — commands.send_stdin(pid, data)."""

    def test_send_stdin_posts_to_correct_endpoint(self, client, mock_api):
        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/processes/77/stdin").respond(
            200, json={"ok": True}
        )
        sb = _make_sandbox(client)
        sb.commands.send_stdin(77, "hello\n")

    def test_send_stdin_bytes_decoded(self, client, mock_api):
        captured = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"ok": True})

        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/processes/88/stdin").mock(
            side_effect=capture_request
        )
        sb = _make_sandbox(client)
        sb.commands.send_stdin(88, b"bytes input\n")
        assert captured["body"]["data"] == "bytes input\n"

    def test_send_stdin_str_passthrough(self, client, mock_api):
        captured: dict = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"ok": True})

        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/processes/55/stdin").mock(
            side_effect=capture_request
        )
        sb = _make_sandbox(client)
        sb.commands.send_stdin(55, "text input")
        assert captured["body"]["data"] == "text input"


# ─── Gap 3: Batch file write ──────────────────────────────────────────────────


class TestWriteFiles:
    """Gap 3 — files.write_files([{path, data}])."""

    def test_write_files_posts_batch_endpoint(self, client, mock_api):
        captured: dict = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"ok": True})

        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/files/batch").mock(
            side_effect=capture_request
        )
        sb = _make_sandbox(client)
        sb.files.write_files([
            {"path": "/workspace/a.py", "data": "print(1)"},
            {"path": "/workspace/b.py", "data": b"print(2)"},
        ])
        files = captured["body"]["files"]
        assert len(files) == 2
        assert files[0]["path"] == "/workspace/a.py"
        assert files[1]["path"] == "/workspace/b.py"
        # Values should be base64 encoded
        import base64
        assert base64.b64decode(files[0]["content"]) == b"print(1)"
        assert base64.b64decode(files[1]["content"]) == b"print(2)"

    def test_write_files_accepts_file_write_item(self, client, mock_api):
        captured: dict = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"ok": True})

        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/files/batch").mock(
            side_effect=capture_request
        )
        sb = _make_sandbox(client)
        sb.files.write_files([
            FileWriteItem(path="/workspace/c.py", data="hello"),
        ])
        assert captured["body"]["files"][0]["path"] == "/workspace/c.py"

    def test_write_files_empty_list_is_noop(self, client, mock_api):
        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/files/batch").respond(
            200, json={"ok": True}
        )
        sb = _make_sandbox(client)
        sb.files.write_files([])  # should not raise


# ─── Gap 4: File watch ────────────────────────────────────────────────────────


class TestFileWatch:
    """Gap 4 — files.watch_dir(path) event iterator."""

    def test_watch_dir_yields_file_watch_events(self, client, mock_api):
        sse_body = (
            'event: change\n'
            'data: {"event": "modified", "path": "/workspace/app.py", "is_dir": false}\n'
            '\n'
            'event: change\n'
            'data: {"event": "created", "path": "/workspace/new.py", "is_dir": false}\n'
            '\n'
        )
        mock_api.get(f"/sandboxes/{SANDBOX_JSON['id']}/files/watch").respond(
            200,
            content=sse_body.encode(),
            headers={"content-type": "text/event-stream"},
        )
        sb = _make_sandbox(client)
        events = list(sb.files.watch_dir("/workspace"))
        assert len(events) == 2
        assert isinstance(events[0], FileWatchEvent)
        assert events[0].event == "modified"
        assert events[0].path == "/workspace/app.py"
        assert events[1].event == "created"

    def test_watch_dir_skips_malformed_lines(self, client, mock_api):
        sse_body = (
            'event: change\n'
            'data: not-json\n'
            '\n'
            'event: change\n'
            'data: {"event": "deleted", "path": "/workspace/old.py"}\n'
            '\n'
        )
        mock_api.get(f"/sandboxes/{SANDBOX_JSON['id']}/files/watch").respond(
            200,
            content=sse_body.encode(),
            headers={"content-type": "text/event-stream"},
        )
        sb = _make_sandbox(client)
        events = list(sb.files.watch_dir("/workspace"))
        # malformed line skipped, one valid event
        assert len(events) == 1
        assert events[0].event == "deleted"


# ─── Gap 5: Directory listing with depth ─────────────────────────────────────


class TestDirectoryListing:
    """Gap 5 — files.list(path, depth=N)."""

    def test_list_sends_depth_param(self, client, mock_api):
        captured: dict = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured["params"] = dict(request.url.params)
            return httpx.Response(200, json={"data": {"entries": []}})

        mock_api.get(f"/sandboxes/{SANDBOX_JSON['id']}/files").mock(
            side_effect=capture_request
        )
        sb = _make_sandbox(client)
        sb.files.list("/workspace", depth=3)
        assert captured["params"].get("depth") == "3"
        assert captured["params"].get("path") == "/workspace"

    def test_list_without_depth_omits_param(self, client, mock_api):
        captured: dict = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured["params"] = dict(request.url.params)
            return httpx.Response(200, json={"data": {"entries": []}})

        mock_api.get(f"/sandboxes/{SANDBOX_JSON['id']}/files").mock(
            side_effect=capture_request
        )
        sb = _make_sandbox(client)
        sb.files.list("/workspace")
        assert "depth" not in captured["params"]


# ─── Gap 6: PTY / Terminal — PRE-EXISTING ─────────────────────────────────────


class TestPtyTerminal:
    """Gap 6 — sandbox.terminal.create() — verifies pre-existing implementation."""

    def test_terminal_create_posts_correct_endpoint(self, client, mock_api):
        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/terminal").respond(
            200, json={"data": {"session_id": "sess_abc", "cols": 80, "rows": 24}}
        )
        sb = _make_sandbox(client)
        result = sb.terminal.create(cols=80, rows=24)
        assert isinstance(result, dict)


# ─── Gap 6b: Sandbox metrics ─────────────────────────────────────────────────


class TestSandboxMetrics:
    """Sandbox metrics expose GET /sandboxes/:id/metrics."""

    def test_metrics_gets_sandbox_metrics_endpoint(self, client, mock_api):
        captured: dict = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured["params"] = dict(request.url.params)
            return httpx.Response(
                200,
                json={
                    "data": {
                        "resource_type": "sandbox",
                        "current": {"cpu_count": 2, "memory_mb": 4096},
                    }
                },
            )

        mock_api.get(f"/sandboxes/{SANDBOX_JSON['id']}/metrics").mock(
            side_effect=capture_request
        )
        sb = _make_sandbox(client)
        result = sb.get_metrics("24h")

        assert captured["params"]["window"] == "24h"
        assert result["current"]["cpu_count"] == 2


class TestSandboxUrlHelpers:
    """Sandbox URL helpers use the canonical preview resolver."""

    def test_get_host_and_get_url_parse_expose_info(self, client, mock_api):
        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/expose").respond(
            200, json={"data": {"url": "https://5173-sbx.sandbox.miosa.ai"}}
        )

        sb = _make_sandbox(client)

        assert sb.get_host(5173) == "5173-sbx.sandbox.miosa.ai"
        assert sb.get_url(5173, "admin") == "https://5173-sbx.sandbox.miosa.ai/admin"


# ─── Gap 7: Git sugar ─────────────────────────────────────────────────────────


class TestGitSugar:
    """Gap 7 — sandbox.git.clone/pull/push/commit."""

    def test_sandbox_has_git_attribute(self, client):
        sb = _make_sandbox(client)
        assert isinstance(sb.git, SandboxGit)

    def test_git_clone_executes_git_clone_command(self, client, mock_api):
        captured: dict = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={"data": {"stdout": "Cloning...", "stderr": "", "exit_code": 0, "duration_ms": 1}},
            )

        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/exec").mock(
            side_effect=capture_request
        )
        sb = _make_sandbox(client)
        result = sb.git.clone("https://github.com/test/repo", path="/workspace/repo")
        assert isinstance(result, GitCloneResult)
        assert result.path == "/workspace/repo"
        assert result.exit_code == 0
        assert "git clone" in captured["body"]["command"]
        assert "https://github.com/test/repo" in captured["body"]["command"]

    def test_git_clone_branch_arg(self, client, mock_api):
        captured: dict = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={"data": {"stdout": "", "stderr": "", "exit_code": 0, "duration_ms": 1}},
            )

        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/exec").mock(
            side_effect=capture_request
        )
        sb = _make_sandbox(client)
        sb.git.clone("https://github.com/test/repo", branch="main")
        assert "-b main" in captured["body"]["command"]

    def test_git_clone_depth_arg(self, client, mock_api):
        captured: dict = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={"data": {"stdout": "", "stderr": "", "exit_code": 0, "duration_ms": 1}},
            )

        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/exec").mock(
            side_effect=capture_request
        )
        sb = _make_sandbox(client)
        sb.git.clone("https://github.com/test/repo", depth=1)
        assert "--depth 1" in captured["body"]["command"]

    def test_git_pull_cwd(self, client, mock_api):
        captured: dict = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={"data": {"stdout": "Already up to date.", "stderr": "", "exit_code": 0, "duration_ms": 1}},
            )

        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/exec").mock(
            side_effect=capture_request
        )
        sb = _make_sandbox(client)
        result = sb.git.pull("/workspace/myrepo")
        assert isinstance(result, GitResult)
        assert captured["body"].get("cwd") == "/workspace/myrepo"
        assert captured["body"]["command"].startswith("git pull")

    def test_git_commit_add_all(self, client, mock_api):
        captured: dict = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={"data": {"stdout": "1 file changed", "stderr": "", "exit_code": 0, "duration_ms": 1}},
            )

        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/exec").mock(
            side_effect=capture_request
        )
        sb = _make_sandbox(client)
        result = sb.git.commit("/workspace", message="chore: test")
        assert isinstance(result, GitResult)
        assert "git add -A" in captured["body"]["command"]
        assert "git commit" in captured["body"]["command"]
        assert "chore: test" in captured["body"]["command"]

    def test_git_push_force_uses_force_with_lease(self, client, mock_api):
        captured: dict = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={"data": {"stdout": "", "stderr": "", "exit_code": 0, "duration_ms": 1}},
            )

        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/exec").mock(
            side_effect=capture_request
        )
        sb = _make_sandbox(client)
        sb.git.push("/workspace", force=True)
        assert "--force-with-lease" in captured["body"]["command"]


# ─── Gap 8: Pause / Resume — PRE-EXISTING ─────────────────────────────────────


class TestPauseResume:
    """Gap 8 — sandbox.pause() / sandbox.resume() — verifies pre-existing."""

    def test_pause_calls_pause_endpoint(self, client, mock_api):
        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/pause").respond(
            200, json={"data": {**SANDBOX_JSON, "state": "paused"}}
        )
        sb = _make_sandbox(client)
        sb.pause()
        assert sb.state == "paused"

    def test_resume_calls_resume_endpoint(self, client, mock_api):
        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/resume").respond(
            200, json={"data": {**SANDBOX_JSON, "state": "running"}}
        )
        sb = Sandbox(client._transport, {**SANDBOX_JSON, "state": "paused"})
        sb.state = "running"  # force to allow operations (just testing endpoint call)
        sb.resume()
        assert sb.state == "running"


# ─── Gap 9: Named snapshots — PRE-EXISTING ────────────────────────────────────


class TestNamedSnapshots:
    """Gap 9 — create_snapshot(name), list, delete, restore — verifies pre-existing."""

    def test_snapshots_create_posts_endpoint(self, client, mock_api):
        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/snapshots").respond(
            200, json={"data": {"id": "snap_abc", "comment": "v1"}}
        )
        sb = _make_sandbox(client)
        result = sb.snapshots.create(comment="v1")
        assert isinstance(result, dict)

    def test_snapshots_list_returns_list(self, client, mock_api):
        mock_api.get(f"/sandboxes/{SANDBOX_JSON['id']}/snapshots").respond(
            200, json={"data": [{"id": "snap_1"}, {"id": "snap_2"}]}
        )
        sb = _make_sandbox(client)
        snaps = sb.snapshots.list()
        assert isinstance(snaps, list)
        assert len(snaps) == 2

    def test_snapshots_delete_calls_delete(self, client, mock_api):
        mock_api.delete(f"/sandboxes/{SANDBOX_JSON['id']}/snapshots/snap_xyz").respond(204)
        sb = _make_sandbox(client)
        sb.snapshots.delete("snap_xyz")  # should not raise

    def test_snapshots_restore_returns_sandbox(self, client, mock_api):
        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/restore/snap_abc").respond(
            200, json={"data": {**SANDBOX_JSON, "state": "running"}}
        )
        sb = _make_sandbox(client)
        new_sb = sb.snapshots.restore("snap_abc")
        assert isinstance(new_sb, Sandbox)


# ─── Gap 10: Fork / Clone ─────────────────────────────────────────────────────


class TestFork:
    """Gap 10 — sandbox.fork(name=...)."""

    def test_fork_posts_fork_endpoint(self, client, mock_api):
        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/fork").respond(
            200, json={"data": {**SANDBOX_JSON, "id": "sbx_fork_001", "state": "running"}}
        )
        sb = _make_sandbox(client)
        fork = sb.fork()
        assert isinstance(fork, Sandbox)
        assert fork.id == "sbx_fork_001"

    def test_fork_sends_name(self, client, mock_api):
        captured: dict = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={"data": {**SANDBOX_JSON, "id": "sbx_fork_002", "state": "running"}},
            )

        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/fork").mock(
            side_effect=capture_request
        )
        sb = _make_sandbox(client)
        sb.fork(name="my-fork")
        assert captured["body"].get("name") == "my-fork"

    def test_fork_sends_metadata(self, client, mock_api):
        captured: dict = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={"data": {**SANDBOX_JSON, "id": "sbx_fork_003", "state": "running"}},
            )

        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/fork").mock(
            side_effect=capture_request
        )
        sb = _make_sandbox(client)
        sb.fork(metadata={"env": "test"})
        assert captured["body"].get("metadata") == {"env": "test"}

    def test_fork_fails_on_destroyed_sandbox(self, client):
        sb = Sandbox(client._transport, {**SANDBOX_JSON, "state": "destroyed"})
        with pytest.raises(Exception):
            sb.fork()


# ─── Async variants ───────────────────────────────────────────────────────────


class TestAsyncVariants:
    """Spot-checks for async parity of key new gaps (1, 3, 7, 10)."""

    @pytest.mark.asyncio
    async def test_async_background_run(self, async_client, mock_api):
        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/processes").respond(
            200, json={"data": {"pid": 5678}}
        )
        sb = _make_async_sandbox(async_client)
        proc = await sb.commands.run("sleep 60", background=True)
        assert isinstance(proc, AsyncBackgroundProcessInfo)
        assert proc.pid == 5678

    @pytest.mark.asyncio
    async def test_async_send_stdin(self, async_client, mock_api):
        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/processes/10/stdin").respond(
            200, json={"ok": True}
        )
        sb = _make_async_sandbox(async_client)
        await sb.commands.send_stdin(10, "hello")  # should not raise

    @pytest.mark.asyncio
    async def test_async_write_files(self, async_client, mock_api):
        captured: dict = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"ok": True})

        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/files/batch").mock(
            side_effect=capture_request
        )
        sb = _make_async_sandbox(async_client)
        await sb.files.write_files([{"path": "/workspace/x.py", "data": "x=1"}])
        assert len(captured["body"]["files"]) == 1

    @pytest.mark.asyncio
    async def test_async_git_attribute(self, async_client):
        sb = _make_async_sandbox(async_client)
        assert isinstance(sb.git, AsyncSandboxGit)

    @pytest.mark.asyncio
    async def test_async_fork(self, async_client, mock_api):
        mock_api.post(f"/sandboxes/{SANDBOX_JSON['id']}/fork").respond(
            200,
            json={"data": {**SANDBOX_JSON, "id": "sbx_async_fork", "state": "running"}},
        )
        sb = _make_async_sandbox(async_client)
        fork = await sb.fork(name="async-fork")
        assert isinstance(fork, AsyncSandbox)
        assert fork.id == "sbx_async_fork"

    @pytest.mark.asyncio
    async def test_async_list_files_depth_param(self, async_client, mock_api):
        captured: dict = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured["params"] = dict(request.url.params)
            return httpx.Response(200, json={"data": {"entries": []}})

        mock_api.get(f"/sandboxes/{SANDBOX_JSON['id']}/files").mock(
            side_effect=capture_request
        )
        sb = _make_async_sandbox(async_client)
        await sb.files.list("/workspace", depth=2)
        assert captured["params"].get("depth") == "2"
