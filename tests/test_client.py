"""Tests for the MIOSA Python SDK client, resources, and error handling."""

from __future__ import annotations

import json

import pytest

from miosa import Miosa
from miosa.errors import (
    AuthenticationError,
    InsufficientCreditsError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)

from .conftest import COMPUTER_JSON, SANDBOX_JSON

# ---------------------------------------------------------------------------
# Client initialization
# ---------------------------------------------------------------------------


class TestClientInit:
    def test_requires_api_key(self):
        with pytest.raises(ValueError, match="No API key"):
            Miosa()

    def test_accepts_api_key_kwarg(self):
        client = Miosa(api_key="msk_u_test")
        assert client._transport._api_key == "msk_u_test"
        client.close()

    def test_reads_env_var(self, monkeypatch):
        monkeypatch.setenv("MIOSA_API_KEY", "msk_u_env")
        client = Miosa()
        assert client._transport._api_key == "msk_u_env"
        client.close()

    def test_custom_base_url(self):
        client = Miosa(api_key="msk_u_test", base_url="https://custom.api/v1")
        assert client._transport._base_url == "https://custom.api/v1"
        client.close()

    def test_context_manager(self):
        with Miosa(api_key="msk_u_test") as client:
            assert client is not None

    def test_repr(self):
        client = Miosa(api_key="msk_u_test", base_url="https://api.miosa.ai/api/v1")
        assert "api.miosa.ai" in repr(client)
        client.close()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrors:
    def test_401_raises_auth_error(self, mock_api, client):
        mock_api.get("/computers").respond(401, json={"error": "Invalid API key"})
        with pytest.raises(AuthenticationError):
            client.computers.list()

    def test_402_raises_insufficient_credits(self, mock_api, client):
        mock_api.post("/computers").respond(402, json={"message": "Insufficient credits"})
        with pytest.raises(InsufficientCreditsError):
            client.computers.create(name="test")

    def test_404_raises_not_found(self, mock_api, client):
        mock_api.get("/computers/nonexistent").respond(404, json={"error": "Not found"})
        with pytest.raises(NotFoundError):
            client.computers.get("nonexistent")

    def test_422_raises_validation_error(self, mock_api, client):
        mock_api.post("/computers").respond(422, json={"errors": ["name is required"]})
        with pytest.raises(ValidationError):
            client.computers.create(name="")

    def test_429_raises_rate_limit_error(self, mock_api, client):
        mock_api.get("/computers").respond(
            429,
            json={"message": "Rate limited", "retry_after": 5.0},
            headers={"retry-after": "5"},
        )
        with pytest.raises(RateLimitError) as exc_info:
            client.computers.list()
        assert exc_info.value.retry_after == 5.0

    def test_500_raises_server_error(self, mock_api, client):
        mock_api.get("/computers").respond(500, json={"error": "Internal server error"})
        with pytest.raises(ServerError):
            client.computers.list()


# ---------------------------------------------------------------------------
# Computers resource
# ---------------------------------------------------------------------------


class TestComputers:
    def test_create(self, mock_api, client):
        mock_api.post("/computers").respond(200, json=COMPUTER_JSON)
        computer = client.computers.create(name="test-agent", size="small")
        assert computer.id == "comp_abc123"
        assert computer.name == "test-agent"
        assert computer.status == "running"

    def test_list(self, mock_api, client):
        mock_api.get("/computers").respond(200, json={"data": [COMPUTER_JSON]})
        computers = client.computers.list()
        assert len(computers) == 1
        assert computers[0].id == "comp_abc123"

    def test_get(self, mock_api, client):
        mock_api.get("/computers/comp_abc123").respond(200, json=COMPUTER_JSON)
        computer = client.computers.get("comp_abc123")
        assert computer.id == "comp_abc123"

    def test_update(self, mock_api, client):
        updated = {**COMPUTER_JSON, "name": "renamed"}
        mock_api.patch("/computers/comp_abc123").respond(200, json=updated)
        computer = client.computers.update("comp_abc123", name="renamed")
        assert computer.name == "renamed"

    def test_delete(self, mock_api, client):
        mock_api.delete("/computers/comp_abc123").respond(200, json={"success": True})
        client.computers.delete("comp_abc123")


# ---------------------------------------------------------------------------
# Native Sandboxes resource
# ---------------------------------------------------------------------------


class TestSandboxes:
    def test_create_defaults_to_sandbox_template(self, mock_api, client):
        route = mock_api.post("/sandboxes").respond(200, json=SANDBOX_JSON)

        sandbox = client.sandboxes.create(name="sandbox-test")

        assert sandbox.id == "sbx_abc123"
        assert sandbox.template_id == "miosa-sandbox"
        assert sandbox.ready is True
        payload = json.loads(route.calls.last.request.content)
        assert payload["template_id"] == "miosa-sandbox"
        assert payload["name"] == "sandbox-test"

    def test_create_accepts_image_alias(self, mock_api, client):
        sandbox_json = {
            **SANDBOX_JSON,
            "template_id": "debian-12-sandbox-v8",
        }
        route = mock_api.post("/sandboxes").respond(200, json=sandbox_json)

        sandbox = client.sandboxes.create(
            name="sandbox-test",
            image="debian-12-sandbox-v8",
        )

        assert sandbox.template_id == "debian-12-sandbox-v8"
        assert route.calls.last.request.content
        assert b"debian-12-sandbox-v8" in route.calls.last.request.content

    def test_create_posts_to_sandboxes_only(self, mock_api, client):
        route = mock_api.post("/sandboxes").respond(200, json=SANDBOX_JSON)

        client.sandboxes.create(
            cpu_count=2,
            memory_mb=2048,
            disk_size_mb=8192,
            timeout_sec=3600,
            env={"NODE_ENV": "development"},
            metadata={"project": "demo"},
            tags=["agent"],
        )

        payload = json.loads(route.calls.last.request.content)
        assert payload["template_id"] == "miosa-sandbox"
        assert payload["cpu_count"] == 2
        assert payload["memory_mb"] == 2048
        assert payload["disk_size_mb"] == 8192
        assert payload["timeout_sec"] == 3600
        assert payload["env"] == {"NODE_ENV": "development"}
        assert payload["metadata"] == {"project": "demo"}
        assert payload["tags"] == ["agent"]

    def test_image_and_template_id_are_mutually_exclusive(self, client):
        with pytest.raises(TypeError, match="either `image` or `template_id`"):
            client.sandboxes.create(
                image="debian-12-sandbox-v8",
                template_id="miosa-sandbox-dev",
            )

    def test_list(self, mock_api, client):
        mock_api.get("/sandboxes").respond(200, json={"data": [SANDBOX_JSON]})
        sandboxes = client.sandboxes.list(state="running")
        assert len(sandboxes) == 1
        assert sandboxes[0].id == "sbx_abc123"

    def test_get(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json=SANDBOX_JSON)
        sandbox = client.sandboxes.get("sbx_abc123")
        assert sandbox.id == "sbx_abc123"
        assert sandbox.boot_path == "snapshot"
        assert sandbox.boot_ms == 166

    def test_connect_aliases_get(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json=SANDBOX_JSON)
        sandbox = client.sandboxes.connect("sbx_abc123")
        assert sandbox.id == "sbx_abc123"

    def test_delete(self, mock_api, client):
        mock_api.delete("/sandboxes/sbx_abc123").respond(200, json={"state": "destroyed"})
        client.sandboxes.delete("sbx_abc123")

    def test_exec_uses_sandbox_endpoint(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json=SANDBOX_JSON)
        route = mock_api.post("/sandboxes/sbx_abc123/exec").respond(
            200,
            json={"data": {"stdout": "hello\n", "stderr": "", "exit_code": 0}},
        )
        sandbox = client.sandboxes.get("sbx_abc123")
        result = sandbox.exec("echo hello", {"cwd": "/workspace"})
        assert result.stdout == "hello\n"
        payload = json.loads(route.calls.last.request.content)
        assert payload == {"command": "echo hello", "cwd": "/workspace"}

    def test_exec_namespaces_keep_callable_parity(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json=SANDBOX_JSON)
        route = mock_api.post("/sandboxes/sbx_abc123/exec").respond(
            200,
            json={"data": {"stdout": "ok\n", "stderr": "", "exit_code": 0}},
        )
        sandbox = client.sandboxes.get("sbx_abc123")

        direct = sandbox.exec("echo ok")
        via_run = sandbox.exec.run("echo ok")
        via_commands = sandbox.commands.run("echo ok")

        assert direct.stdout == "ok\n"
        assert via_run.exit_code == 0
        assert via_commands.exit_code == 0
        assert route.calls.call_count == 3

    def test_exec_stream_uses_native_sandbox_sse(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json=SANDBOX_JSON)
        route = mock_api.post("/sandboxes/sbx_abc123/exec/stream").respond(
            200,
            content=b'event: stdout\ndata: {"line":"ok"}\n\n',
            headers={"content-type": "text/event-stream"},
        )
        sandbox = client.sandboxes.get("sbx_abc123")

        events = list(sandbox.exec.stream("echo ok"))

        assert events[0].type == "stdout"
        assert events[0].data == {"line": "ok"}
        assert b"echo ok" in route.calls.last.request.content

    def test_write_file_and_expose_use_sandbox_endpoint(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json=SANDBOX_JSON)
        write_route = mock_api.post("/sandboxes/sbx_abc123/files").respond(200, json={"ok": True})
        expose_route = mock_api.post("/sandboxes/sbx_abc123/expose").respond(
            200,
            json={"url": "https://3000-sbxabc.sandbox.miosa.app"},
        )
        sandbox = client.sandboxes.get("sbx_abc123")
        sandbox.write_file("/workspace/index.html", "<h1>ok</h1>")
        preview = sandbox.expose(3000)
        assert preview == "https://3000-sbxabc.sandbox.miosa.app"
        assert b"/workspace/index.html" in write_route.calls.last.request.content
        assert b"3000" in expose_route.calls.last.request.content

    def test_file_namespaces_use_native_sandbox_endpoints(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json=SANDBOX_JSON)
        list_route = mock_api.get("/sandboxes/sbx_abc123/files").respond(
            200,
            json={"data": {"path": "/workspace", "entries": [{"name": "app.txt"}]}},
        )
        stat_route = mock_api.post("/sandboxes/sbx_abc123/files/stat").respond(
            200,
            json={"data": {"path": "/workspace/app.txt", "size": 5}},
        )
        mock_api.get("/sandboxes/sbx_abc123/files/workspace/app.txt").respond(
            200,
            content=b"hello",
            headers={"content-type": "application/octet-stream"},
        )

        sandbox = client.sandboxes.get("sbx_abc123")
        files = sandbox.files.list("/workspace")
        stat = sandbox.files.stat("/workspace/app.txt")
        content = sandbox.files.read_text("/workspace/app.txt")

        assert files["entries"][0]["name"] == "app.txt"
        assert stat["size"] == 5
        assert content == "hello"
        assert b"path=%2Fworkspace" in list_route.calls.last.request.url.query
        assert b"/workspace/app.txt" in stat_route.calls.last.request.content

    def test_logs_snapshots_and_lifecycle_use_native_sandbox_endpoints(self, mock_api, client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json=SANDBOX_JSON)
        logs_route = mock_api.get("/sandboxes/sbx_abc123/logs").respond(
            200,
            json={"data": {"lines": ["ready"]}},
        )
        mock_api.get("/sandboxes/sbx_abc123/logs/stream").respond(
            200,
            content=b'event: log\ndata: {"line":"ready"}\n\n',
            headers={"content-type": "text/event-stream"},
        )
        create_snapshot_route = mock_api.post("/sandboxes/sbx_abc123/snapshots").respond(
            200,
            json={"data": {"id": "snap_1", "sandbox_id": "sbx_abc123"}},
        )
        mock_api.get("/sandboxes/sbx_abc123/snapshots").respond(
            200,
            json={"data": [{"id": "snap_1", "sandbox_id": "sbx_abc123"}]},
        )
        mock_api.post("/sandboxes/sbx_abc123/restore/snap_1").respond(
            200,
            json={"data": {**SANDBOX_JSON, "id": "sbx_restored"}},
        )
        delete_snapshot_route = mock_api.delete("/sandboxes/sbx_abc123/snapshots/snap_1").respond(
            200, json={"ok": True}
        )
        mock_api.post("/sandboxes/sbx_abc123/pause").respond(
            200,
            json={"data": {**SANDBOX_JSON, "state": "paused"}},
        )
        mock_api.post("/sandboxes/sbx_abc123/resume").respond(
            200,
            json={"data": SANDBOX_JSON},
        )
        deploy_route = mock_api.post("/sandboxes/sbx_abc123/deploy").respond(
            200,
            json={"data": {"deployment_id": "dep_1", "url": "https://app.miosa.app"}},
        )

        sandbox = client.sandboxes.get("sbx_abc123")
        logs = sandbox.logs.get(100)
        log_events = list(sandbox.logs.stream())
        created = sandbox.snapshots.create("checkpoint")
        snapshots = sandbox.snapshots.list()
        restored = sandbox.snapshots.restore("snap_1")
        sandbox.snapshots.delete("snap_1")
        sandbox.pause()
        sandbox.resume()
        deployment = sandbox.deploy(
            name="site",
            source_path="/workspace/dist",
            custom_domain="example.com",
        )

        assert logs == {"lines": ["ready"]}
        assert log_events[0].data == {"line": "ready"}
        assert created["id"] == "snap_1"
        assert snapshots[0]["id"] == "snap_1"
        assert restored.id == "sbx_restored"
        assert delete_snapshot_route.calls.call_count == 1
        assert sandbox.state == "running"
        assert deployment["deployment_id"] == "dep_1"
        assert b"lines=100" in logs_route.calls.last.request.url.query
        assert b"checkpoint" in create_snapshot_route.calls.last.request.content
        assert b"example.com" in deploy_route.calls.last.request.content

    def test_build_spec_schema_and_validation_use_template_endpoints(self, mock_api, client):
        mock_api.get("/sandbox-templates/build-spec").respond(
            200,
            json={"version": "2026-05-13", "fields": {"from": "OCI base"}},
        )
        route = mock_api.post("/sandbox-templates/validate").respond(
            200,
            json={
                "valid": True,
                "build_spec": {
                    "from": "node:22-bookworm",
                    "startCmd": "pnpm dev --host 0.0.0.0 --port 3000",
                },
            },
        )

        schema = client.sandboxes.get_build_spec_schema()
        result = client.sandboxes.validate_build_spec(
            {
                "from": "node:22-bookworm",
                "startCmd": "pnpm dev --host 0.0.0.0 --port 3000",
            }
        )

        assert schema["version"] == "2026-05-13"
        assert result["valid"] is True
        payload = json.loads(route.calls.last.request.content)
        assert payload["build_spec"]["from"] == "node:22-bookworm"

    def test_custom_template_build_endpoints(self, mock_api, client):
        create_template_route = mock_api.post("/sandbox-templates").respond(
            201,
            json={
                "data": {
                    "id": "tpl_123",
                    "name": "Agent Web App",
                    "slug": "agent-web-app",
                    "status": "draft",
                }
            },
        )
        create_build_route = mock_api.post("/sandbox-templates/tpl_123/builds").respond(
            201,
            json={
                "data": {
                    "id": "build_123",
                    "sandbox_template_id": "tpl_123",
                    "state": "queued",
                }
            },
        )
        mock_api.get("/sandbox-templates/tpl_123/builds").respond(
            200,
            json={
                "data": [
                    {
                        "id": "build_123",
                        "sandbox_template_id": "tpl_123",
                        "state": "queued",
                    }
                ]
            },
        )
        mock_api.get("/sandbox-template-builds/build_123").respond(
            200,
            json={
                "data": {
                    "id": "build_123",
                    "sandbox_template_id": "tpl_123",
                    "state": "queued",
                }
            },
        )

        template = client.sandboxes.create_template(
            name="Agent Web App",
            slug="agent-web-app",
            build_spec={"from": "node:22-bookworm"},
        )
        build = client.sandboxes.create_template_build("tpl_123")
        builds = client.sandboxes.list_template_builds("tpl_123")
        fetched = client.sandboxes.get_template_build("build_123")

        assert template["data"]["id"] == "tpl_123"
        assert build["data"]["state"] == "queued"
        assert builds["data"][0]["id"] == "build_123"
        assert fetched["data"]["id"] == "build_123"
        create_template_payload = json.loads(create_template_route.calls.last.request.content)
        assert create_template_payload["build_spec"]["from"] == "node:22-bookworm"
        assert json.loads(create_build_route.calls.last.request.content) == {}

    def test_canonical_sandbox_surface_never_calls_computers(self, mock_api, client):
        computer_route = mock_api.route(path__regex=r"^/computers(/.*)?$").respond(
            599,
            json={"error": "sandbox surface must not call computers"},
        )
        mock_api.post("/sandboxes").respond(200, json={"data": SANDBOX_JSON})
        mock_api.get("/sandboxes").respond(200, json={"data": [SANDBOX_JSON]})
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json=SANDBOX_JSON)
        mock_api.delete("/sandboxes/sbx_abc123").respond(200, json={"state": "destroyed"})
        mock_api.post("/sandboxes/sbx_abc123/exec").respond(
            200,
            json={"data": {"stdout": "ok\n", "stderr": "", "exit_code": 0}},
        )
        mock_api.post("/sandboxes/sbx_abc123/files").respond(200, json={"ok": True})
        mock_api.get("/sandboxes/sbx_abc123/files").respond(
            200,
            json={"data": {"path": "/workspace", "entries": []}},
        )
        mock_api.get("/sandboxes/sbx_abc123/files/workspace/app.txt").respond(
            200,
            content=b"ok",
            headers={"content-type": "application/octet-stream"},
        )
        mock_api.post("/sandboxes/sbx_abc123/files/stat").respond(
            200,
            json={"data": {"path": "/workspace/app.txt", "size": 2}},
        )
        mock_api.post("/sandboxes/sbx_abc123/expose").respond(
            200,
            json={"data": {"url": "https://5173-sbx.sandbox.miosa.app"}},
        )
        mock_api.get("/sandboxes/sbx_abc123/artifacts").respond(
            200,
            json={"data": {"artifacts": {}}},
        )
        mock_api.get("/sandboxes/sbx_abc123/logs").respond(
            200,
            json={"data": {"lines": []}},
        )
        mock_api.post("/sandboxes/sbx_abc123/snapshots").respond(
            200,
            json={"data": {"id": "snap_1", "sandbox_id": "sbx_abc123"}},
        )
        mock_api.get("/sandboxes/sbx_abc123/snapshots").respond(200, json={"data": []})
        mock_api.post("/sandboxes/sbx_abc123/restore/snap_1").respond(
            200,
            json={"data": {**SANDBOX_JSON, "id": "sbx_restored"}},
        )
        mock_api.delete("/sandboxes/sbx_abc123/snapshots/snap_1").respond(200, json={})
        mock_api.post("/sandboxes/sbx_abc123/pause").respond(
            200,
            json={"data": {**SANDBOX_JSON, "state": "paused"}},
        )
        mock_api.post("/sandboxes/sbx_abc123/resume").respond(200, json={"data": SANDBOX_JSON})
        mock_api.post("/sandboxes/sbx_abc123/deploy").respond(
            200,
            json={"data": {"deployment_id": "dep_1"}},
        )
        mock_api.get("/sandbox-templates").respond(200, json={"data": []})
        mock_api.get("/sandbox-templates/miosa-sandbox").respond(
            200,
            json={"id": "miosa-sandbox"},
        )

        sandbox = client.sandboxes.create()
        client.sandboxes.list()
        client.sandboxes.get("sbx_abc123")
        client.sandboxes.connect("sbx_abc123")
        client.sandboxes.list_templates()
        client.sandboxes.get_template("miosa-sandbox")
        sandbox.commands.run("echo ok")
        sandbox.files.write("/workspace/app.txt", "ok")
        sandbox.files.read_text("/workspace/app.txt")
        sandbox.files.list("/workspace")
        sandbox.files.stat("/workspace/app.txt")
        sandbox.preview.expose(5173)
        sandbox.artifacts.list()
        sandbox.logs.get(10)
        sandbox.snapshots.create("checkpoint")
        sandbox.snapshots.list()
        sandbox.snapshots.restore("snap_1")
        sandbox.snapshots.delete("snap_1")
        sandbox.pause()
        sandbox.resume()
        sandbox.deploy(name="site", source_path="/workspace/dist")
        client.sandboxes.delete("sbx_abc123")

        assert computer_route.calls.call_count == 0


# ---------------------------------------------------------------------------
# Computer bound object
# ---------------------------------------------------------------------------


class TestComputerActions:
    @pytest.fixture
    def computer(self, mock_api, client):
        mock_api.get("/computers/comp_abc123").respond(200, json=COMPUTER_JSON)
        return client.computers.get("comp_abc123")

    def test_start(self, mock_api, computer):
        mock_api.post("/computers/comp_abc123/start").respond(
            200, json={"success": True, "message": "started"}
        )
        result = computer.start()
        assert result.success is True

    def test_stop(self, mock_api, computer):
        mock_api.post("/computers/comp_abc123/stop").respond(200, json={"success": True})
        result = computer.stop()
        assert result.success is True

    def test_restart(self, mock_api, computer):
        mock_api.post("/computers/comp_abc123/restart").respond(200, json={"success": True})
        result = computer.restart()
        assert result.success is True

    def test_destroy(self, mock_api, computer):
        mock_api.delete("/computers/comp_abc123").respond(200, json={"success": True})
        result = computer.destroy()
        assert result.success is True

    def test_refresh(self, mock_api, computer):
        updated = {**COMPUTER_JSON, "status": "stopped"}
        mock_api.get("/computers/comp_abc123").respond(200, json=updated)
        computer.refresh()
        assert computer.status == "stopped"

    def test_repr(self, computer):
        r = repr(computer)
        assert "comp_abc123" in r
        assert "test-agent" in r


# ---------------------------------------------------------------------------
# Desktop control
# ---------------------------------------------------------------------------


class TestDesktop:
    @pytest.fixture
    def computer(self, mock_api, client):
        mock_api.get("/computers/comp_abc123").respond(200, json=COMPUTER_JSON)
        return client.computers.get("comp_abc123")

    def test_screenshot(self, mock_api, computer):
        png_bytes = b"\x89PNG\r\n\x1a\nfakeimage"
        mock_api.get("/computers/comp_abc123/desktop/screenshot").respond(
            200,
            content=png_bytes,
            headers={"content-type": "image/png"},
        )
        result = computer.screenshot()
        assert result == png_bytes

    def test_screenshot_returns_bytes_with_png_header(self, mock_api, computer):
        # Verify screenshot returns raw bytes and that the PNG magic bytes
        # are preserved exactly (bytes, not str, not base64-decoded/re-encoded).
        png_magic = b"\x89PNG\r\n\x1a\n"
        fake_png = png_magic + b"\x00" * 16 + b"FAKE_IDAT_CHUNK"
        mock_api.get("/computers/comp_abc123/desktop/screenshot").respond(
            200,
            content=fake_png,
            headers={"content-type": "image/png"},
        )
        result = computer.screenshot()
        assert isinstance(result, bytes), "screenshot() must return bytes"
        assert result[:8] == png_magic, "first 8 bytes must be the PNG magic header"
        assert result == fake_png

    def test_click(self, mock_api, computer):
        mock_api.post("/computers/comp_abc123/desktop/click").respond(200, json={"success": True})
        result = computer.click(100, 200)
        assert result.success is True

    def test_double_click(self, mock_api, computer):
        mock_api.post("/computers/comp_abc123/desktop/double-click").respond(
            200, json={"success": True}
        )
        result = computer.double_click(100, 200)
        assert result.success is True

    def test_type(self, mock_api, computer):
        mock_api.post("/computers/comp_abc123/desktop/type").respond(200, json={"success": True})
        result = computer.type("hello world")
        assert result.success is True

    def test_key(self, mock_api, computer):
        mock_api.post("/computers/comp_abc123/desktop/key").respond(200, json={"success": True})
        result = computer.key("Enter")
        assert result.success is True

    def test_scroll(self, mock_api, computer):
        mock_api.post("/computers/comp_abc123/desktop/scroll").respond(200, json={"success": True})
        result = computer.scroll("down", 3)
        assert result.success is True

    def test_drag(self, mock_api, computer):
        mock_api.post("/computers/comp_abc123/desktop/drag").respond(200, json={"success": True})
        result = computer.drag(10, 10, 200, 200)
        assert result.success is True

    def test_wait(self, mock_api, computer):
        mock_api.post("/computers/comp_abc123/desktop/wait").respond(200, json={"success": True})
        result = computer.wait(5)
        assert result.success is True

    def test_cursor(self, mock_api, computer):
        mock_api.get("/computers/comp_abc123/desktop/cursor").respond(
            200, json={"x": 512, "y": 384}
        )
        pos = computer.cursor()
        assert pos.x == 512
        assert pos.y == 384

    def test_windows(self, mock_api, computer):
        mock_api.get("/computers/comp_abc123/desktop/windows").respond(
            200,
            json={"data": [{"id": "w1", "title": "Terminal", "focused": True}]},
        )
        wins = computer.windows()
        assert len(wins) == 1
        assert wins[0].title == "Terminal"

    def test_focus_window(self, mock_api, computer):
        mock_api.post("/computers/comp_abc123/desktop/window/focus").respond(
            200, json={"success": True}
        )
        result = computer.focus_window("w1")
        assert result.success is True

    def test_launch(self, mock_api, computer):
        mock_api.post("/computers/comp_abc123/desktop/launch").respond(200, json={"success": True})
        result = computer.launch("firefox")
        assert result.success is True


# ---------------------------------------------------------------------------
# Exec
# ---------------------------------------------------------------------------


class TestExec:
    @pytest.fixture
    def computer(self, mock_api, client):
        mock_api.get("/computers/comp_abc123").respond(200, json=COMPUTER_JSON)
        return client.computers.get("comp_abc123")

    def test_bash(self, mock_api, computer):
        mock_api.post("/computers/comp_abc123/exec").respond(
            200, json={"output": "total 8\ndrwxr-xr-x", "success": True}
        )
        result = computer.bash("ls -la")
        assert result.success is True
        assert "total 8" in result.output

    def test_python(self, mock_api, computer):
        mock_api.post("/computers/comp_abc123/exec/python").respond(
            200, json={"output": "4\n", "success": True}
        )
        result = computer.python("print(2+2)")
        assert result.success is True
        assert "4" in result.output

    def test_run_alias(self, mock_api, computer):
        mock_api.post("/computers/comp_abc123/exec").respond(
            200, json={"output": "2\n", "success": True}
        )
        result = computer.run("python3 -c 'print(1+1)'")
        assert result.success is True
        assert result.output == "2\n"


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


class TestFiles:
    @pytest.fixture
    def computer(self, mock_api, client):
        mock_api.get("/computers/comp_abc123").respond(200, json=COMPUTER_JSON)
        return client.computers.get("comp_abc123")

    def test_list_files(self, mock_api, computer):
        mock_api.get("/computers/comp_abc123/files").respond(
            200,
            json={
                "data": [
                    {
                        "name": "readme.txt",
                        "path": "/home/user/readme.txt",
                        "is_dir": False,
                        "size": 42,
                    }
                ]
            },
        )
        files = computer.files.list("/home/user")
        assert len(files) == 1
        assert files[0].name == "readme.txt"

    def test_download(self, mock_api, computer):
        content = b"file content here"
        mock_api.get("/computers/comp_abc123/files/download").respond(
            200,
            content=content,
            headers={"content-type": "application/octet-stream"},
        )
        result = computer.files.download("/home/user/readme.txt")
        assert result == content

    def test_upload(self, mock_api, computer, tmp_path):
        local_file = tmp_path / "test.txt"
        local_file.write_text("hello")
        mock_api.post("/computers/comp_abc123/files/upload").respond(200, json={"success": True})
        result = computer.files.upload(str(local_file), "/home/user/test.txt")
        assert result.success is True

    def test_direct_write_and_read_file_aliases(self, mock_api, computer):
        mock_api.post("/computers/comp_abc123/files/write").respond(200, json={"success": True})
        computer.write_file("/workspace/foo.txt", "hello")

        mock_api.get("/computers/comp_abc123/files/download").respond(
            200,
            content=b"hello",
            headers={"content-type": "application/octet-stream"},
        )
        assert computer.read_file("/workspace/foo.txt") == "hello"

    def test_write_file_sends_content_base64_field(self, mock_api, computer):
        import base64
        import json as _json

        route = mock_api.post("/computers/comp_abc123/files/write").respond(
            200, json={"success": True}
        )
        computer.write_file("/workspace/script.py", b"print('hello')")

        payload = _json.loads(route.calls.last.request.content)
        assert "content_base64" in payload, "request body must contain content_base64 field"
        assert payload["path"] == "/workspace/script.py"

        decoded = base64.b64decode(payload["content_base64"])
        assert decoded == b"print('hello')"

    def test_write_file_base64_encodes_text_content(self, mock_api, computer):
        import base64
        import json as _json

        route = mock_api.post("/computers/comp_abc123/files/write").respond(
            200, json={"success": True}
        )
        computer.write_file("/workspace/hello.txt", "hello, world\n")

        payload = _json.loads(route.calls.last.request.content)
        decoded = base64.b64decode(payload["content_base64"])
        assert decoded == b"hello, world\n"

    def test_delete_file(self, mock_api, computer):
        mock_api.delete("/computers/comp_abc123/files").respond(200, json={"success": True})
        result = computer.files.delete("/home/user/readme.txt")
        assert result.success is True

    def test_export(self, mock_api, computer):
        mock_api.post("/computers/comp_abc123/files/export").respond(200, json={"success": True})
        result = computer.files.export("/home/user/readme.txt")
        assert result.success is True


# ---------------------------------------------------------------------------
# Agent / CUA sessions
# ---------------------------------------------------------------------------

SESSION_JSON = {
    "id": "sess_xyz789",
    "computer_id": "comp_abc123",
    "goal": "Open Firefox",
    "status": "running",
    "model_id": "nemotron-3-super",
    "max_turns": 50,
    "turns_used": 3,
    "result": None,
    "error": None,
    "created_at": "2026-04-01T00:00:00Z",
    "updated_at": "2026-04-01T00:00:00Z",
}


class TestAgent:
    @pytest.fixture
    def computer(self, mock_api, client):
        mock_api.get("/computers/comp_abc123").respond(200, json=COMPUTER_JSON)
        return client.computers.get("comp_abc123")

    def test_run(self, mock_api, computer):
        mock_api.post("/computers/comp_abc123/cua/sessions").respond(200, json=SESSION_JSON)
        session = computer.agent.run(goal="Open Firefox", model_id="nemotron-3-super")
        assert session.id == "sess_xyz789"
        assert session.goal == "Open Firefox"
        assert session.status.value == "running"

    def test_list_sessions(self, mock_api, computer):
        mock_api.get("/computers/comp_abc123/cua/sessions").respond(
            200, json={"data": [SESSION_JSON]}
        )
        sessions = computer.agent.list()
        assert len(sessions) == 1

    def test_get_session(self, mock_api, computer):
        mock_api.get("/computers/comp_abc123/cua/sessions/sess_xyz789").respond(
            200, json=SESSION_JSON
        )
        session = computer.agent.get("sess_xyz789")
        assert session.id == "sess_xyz789"

    def test_cancel_session(self, mock_api, computer):
        cancelled = {**SESSION_JSON, "status": "cancelled"}
        mock_api.delete("/computers/comp_abc123/cua/sessions/sess_xyz789").respond(
            200, json=cancelled
        )
        session = computer.agent.cancel("sess_xyz789")
        assert session.status.value == "cancelled"


# ---------------------------------------------------------------------------
# Credits
# ---------------------------------------------------------------------------


class TestCredits:
    def test_get_balance(self, mock_api, client):
        mock_api.get("/credits/balance").respond(200, json={"balance": 4200.0, "plan": "pro"})
        balance = client.get_balance()
        assert balance.balance == 4200.0
        assert balance.plan == "pro"

    def test_get_transactions(self, mock_api, client):
        mock_api.get("/credits/transactions").respond(
            200,
            json={
                "data": [
                    {
                        "id": "txn_1",
                        "amount": -10.0,
                        "type": "compute",
                        "description": "Small VM 1h",
                    }
                ]
            },
        )
        txns = client.get_transactions()
        assert len(txns.data) == 1
        assert txns.data[0].amount == -10.0

    def test_get_usage(self, mock_api, client):
        mock_api.get("/credits/usage").respond(
            200, json={"compute": 100.0, "ai": 50.0, "total": 150.0}
        )
        usage = client.get_usage()
        assert usage.total == 150.0


# ---------------------------------------------------------------------------
# Async client
# ---------------------------------------------------------------------------


class TestAsyncClient:
    @pytest.mark.asyncio
    async def test_create_computer(self, mock_api, async_client):
        mock_api.post("/computers").respond(200, json=COMPUTER_JSON)
        computer = await async_client.computers.create(name="test-agent")
        assert computer.id == "comp_abc123"
        await async_client.close()

    @pytest.mark.asyncio
    async def test_click(self, mock_api, async_client):
        mock_api.get("/computers/comp_abc123").respond(200, json=COMPUTER_JSON)
        mock_api.post("/computers/comp_abc123/desktop/click").respond(200, json={"success": True})
        computer = await async_client.computers.get("comp_abc123")
        result = await computer.click(100, 200)
        assert result.success is True
        await async_client.close()

    @pytest.mark.asyncio
    async def test_bash(self, mock_api, async_client):
        mock_api.get("/computers/comp_abc123").respond(200, json=COMPUTER_JSON)
        mock_api.post("/computers/comp_abc123/exec").respond(
            200, json={"output": "hello", "success": True}
        )
        computer = await async_client.computers.get("comp_abc123")
        result = await computer.bash("echo hello")
        assert result.output == "hello"
        await async_client.close()

    @pytest.mark.asyncio
    async def test_get_balance(self, mock_api, async_client):
        mock_api.get("/credits/balance").respond(200, json={"balance": 1000.0, "plan": "starter"})
        balance = await async_client.get_balance()
        assert balance.balance == 1000.0
        await async_client.close()

    @pytest.mark.asyncio
    async def test_sandbox_native_namespaces(self, mock_api, async_client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json=SANDBOX_JSON)
        exec_route = mock_api.post("/sandboxes/sbx_abc123/exec").respond(
            200,
            json={"data": {"stdout": "ok\n", "stderr": "", "exit_code": 0}},
        )
        mock_api.post("/sandboxes/sbx_abc123/files").respond(200, json={"ok": True})
        mock_api.get("/sandboxes/sbx_abc123/files").respond(
            200,
            json={"data": {"path": "/workspace", "entries": [{"name": "app.txt"}]}},
        )
        mock_api.post("/sandboxes/sbx_abc123/files/stat").respond(
            200,
            json={"data": {"path": "/workspace/app.txt", "size": 5}},
        )
        mock_api.get("/sandboxes/sbx_abc123/files/workspace/app.txt").respond(
            200,
            content=b"hello",
            headers={"content-type": "application/octet-stream"},
        )
        mock_api.post("/sandboxes/sbx_abc123/expose").respond(
            200,
            json={"data": {"url": "https://5173-sbx.sandbox.miosa.app"}},
        )
        mock_api.get("/sandboxes/sbx_abc123/logs").respond(
            200,
            json={"data": {"lines": ["ready"]}},
        )
        mock_api.post("/sandboxes/sbx_abc123/snapshots").respond(
            200,
            json={"data": {"id": "snap_1", "sandbox_id": "sbx_abc123"}},
        )
        mock_api.get("/sandboxes/sbx_abc123/snapshots").respond(
            200,
            json={"data": [{"id": "snap_1", "sandbox_id": "sbx_abc123"}]},
        )
        mock_api.post("/sandboxes/sbx_abc123/restore/snap_1").respond(
            200,
            json={"data": {**SANDBOX_JSON, "id": "sbx_restored"}},
        )
        mock_api.delete("/sandboxes/sbx_abc123/snapshots/snap_1").respond(
            200,
            json={"ok": True},
        )
        mock_api.post("/sandboxes/sbx_abc123/pause").respond(
            200,
            json={"data": {**SANDBOX_JSON, "state": "paused"}},
        )
        mock_api.post("/sandboxes/sbx_abc123/resume").respond(
            200,
            json={"data": SANDBOX_JSON},
        )
        mock_api.post("/sandboxes/sbx_abc123/deploy").respond(
            200,
            json={"data": {"deployment_id": "dep_1"}},
        )

        sandbox = await async_client.sandboxes.get("sbx_abc123")
        direct = await sandbox.exec("echo ok")
        via_run = await sandbox.exec.run("echo ok")
        via_commands = await sandbox.commands.run("echo ok")
        await sandbox.files.write("/workspace/app.txt", "hello")
        files = await sandbox.files.list("/workspace")
        stat = await sandbox.files.stat("/workspace/app.txt")
        text = await sandbox.files.read_text("/workspace/app.txt")
        preview = await sandbox.preview.expose(5173)
        logs = await sandbox.logs.get(100)
        created = await sandbox.snapshots.create("checkpoint")
        snapshots = await sandbox.snapshots.list()
        restored = await sandbox.snapshots.restore("snap_1")
        await sandbox.snapshots.delete("snap_1")
        await sandbox.pause()
        await sandbox.resume()
        deployment = await sandbox.deploy(source_path="/workspace/dist")

        assert direct.stdout == "ok\n"
        assert via_run.exit_code == 0
        assert via_commands.exit_code == 0
        assert exec_route.calls.call_count == 3
        assert files["entries"][0]["name"] == "app.txt"
        assert stat["size"] == 5
        assert text == "hello"
        assert preview == "https://5173-sbx.sandbox.miosa.app"
        assert logs == {"lines": ["ready"]}
        assert created["id"] == "snap_1"
        assert snapshots[0]["id"] == "snap_1"
        assert restored.id == "sbx_restored"
        assert sandbox.state == "running"
        assert deployment["deployment_id"] == "dep_1"
        await async_client.close()

    @pytest.mark.asyncio
    async def test_sandbox_connect_aliases_get(self, mock_api, async_client):
        mock_api.get("/sandboxes/sbx_abc123").respond(200, json=SANDBOX_JSON)
        sandbox = await async_client.sandboxes.connect("sbx_abc123")
        assert sandbox.id == "sbx_abc123"
        await async_client.close()
