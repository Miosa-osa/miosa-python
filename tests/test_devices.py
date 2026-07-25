"""Tests for the unified devices SDK resource."""

from __future__ import annotations

import json


def test_devices_list_show_capabilities_and_exec(mock_api, client):
    list_route = mock_api.get(
        "/devices",
        params={"kind": "sandbox", "workspace_id": "ws_123", "project_id": "prj_123"},
    ).respond(200, json={"data": [{"id": "sbx_123", "kind": "sandbox", "ready": True}]})
    show_route = mock_api.get("/devices/sbx_123").respond(
        200, json={"data": {"id": "sbx_123", "kind": "sandbox"}}
    )
    capabilities_route = mock_api.get("/devices/sbx_123/capabilities").respond(
        200, json={"data": {"id": "sbx_123", "capabilities": {"files": True}}}
    )
    exec_route = mock_api.post("/devices/sbx_123/exec").respond(
        200, json={"data": {"exit_code": 0, "stdout": "ok\n"}}
    )

    listed = client.devices.list(kind="sandbox", workspace_id="ws_123", project_id="prj_123")
    shown = client.devices.get("sbx_123")
    caps = client.devices.capabilities("sbx_123")
    result = client.devices.exec(
        "sbx_123",
        "printf ok",
        timeout_ms=30_000,
        cwd="/workspace",
        env={"NODE_ENV": "test"},
    )

    exec_body = json.loads(exec_route.calls.last.request.content)

    assert list_route.called
    assert show_route.called
    assert capabilities_route.called
    assert listed[0]["id"] == "sbx_123"
    assert shown["kind"] == "sandbox"
    assert caps["capabilities"]["files"] is True
    assert exec_body == {
        "command": "printf ok",
        "timeout_ms": 30_000,
        "cwd": "/workspace",
        "env": {"NODE_ENV": "test"},
    }
    assert result["stdout"] == "ok\n"


def test_devices_files_and_expose(mock_api, client):
    list_files_route = mock_api.get(
        "/devices/sbx_123/files", params={"path": "/workspace"}
    ).respond(200, json={"data": [{"path": "/workspace/out.html", "type": "file"}]})
    read_route = mock_api.get(
        "/devices/sbx_123/files/read", params={"path": "/workspace/out.html"}
    ).respond(
        200,
        json={
            "data": {
                "path": "/workspace/out.html",
                "encoding": "base64",
                "content": "PGgxPk9LPC9oMT4=",
            }
        },
    )
    write_route = mock_api.post("/devices/sbx_123/files/write").respond(
        200, json={"data": {"path": "/workspace/out.html", "size": 11}}
    )
    expose_route = mock_api.post("/devices/sbx_123/expose").respond(
        200,
        json={
            "data": {
                "port": 3000,
                "url": "https://3000-sbx.sandbox.miosa.ai",
            }
        },
    )

    files = client.devices.list_files("sbx_123", path="/workspace")
    read = client.devices.read_file("sbx_123", "/workspace/out.html")
    written = client.devices.write_file(
        "sbx_123", "/workspace/out.html", content_base64="PGgxPk9LPC9oMT4="
    )
    exposed = client.devices.expose("sbx_123", 3000)

    write_body = json.loads(write_route.calls.last.request.content)
    expose_body = json.loads(expose_route.calls.last.request.content)

    assert list_files_route.called
    assert read_route.called
    assert files[0]["path"] == "/workspace/out.html"
    assert read["encoding"] == "base64"
    assert write_body == {
        "path": "/workspace/out.html",
        "content_base64": "PGgxPk9LPC9oMT4=",
    }
    assert written["size"] == 11
    assert expose_body == {"port": 3000}
    assert exposed["url"].endswith(".sandbox.miosa.ai")


def test_devices_lifecycle(mock_api, client):
    pause_route = mock_api.post("/devices/sbx_123/pause").respond(
        200, json={"data": {"id": "sbx_123", "state": "paused"}}
    )
    stop_route = mock_api.post("/devices/sbx_123/stop").respond(
        200, json={"data": {"id": "sbx_123", "state": "stopped"}}
    )
    resume_route = mock_api.post("/devices/sbx_123/resume").respond(
        200, json={"data": {"id": "sbx_123", "state": "running"}}
    )
    extend_route = mock_api.post("/devices/sbx_123/extend").respond(
        200, json={"data": {"id": "sbx_123", "timeout_sec": 7200}}
    )
    destroy_route = mock_api.delete("/devices/sbx_123").respond(
        200, json={"data": {"id": "sbx_123", "state": "destroyed"}}
    )

    paused = client.devices.pause("sbx_123")
    stopped = client.devices.stop("sbx_123")
    resumed = client.devices.resume("sbx_123")
    extended = client.devices.extend("sbx_123", 7200)
    destroyed = client.devices.destroy("sbx_123")

    assert pause_route.called
    assert stop_route.called
    assert resume_route.called
    assert json.loads(extend_route.calls.last.request.content) == {"timeout_sec": 7200}
    assert destroy_route.called
    assert paused["state"] == "paused"
    assert stopped["state"] == "stopped"
    assert resumed["state"] == "running"
    assert extended["timeout_sec"] == 7200
    assert destroyed["state"] == "destroyed"


def test_devices_bootstrap(mock_api, client):
    write_route = mock_api.post("/devices/sbx_123/files/write").respond(
        200, json={"data": {"path": "/workspace/.miosa/runtime-bootstrap.json"}}
    )
    exec_route = mock_api.post("/devices/sbx_123/exec").respond(
        200, json={"data": {"exit_code": 0, "stdout": "runtime available\n"}}
    )

    result = client.devices.bootstrap(
        "sbx_123",
        runtime="claude-code",
        connectors=["anthropic/workspace-claude"],
        env={"ANTHROPIC_API_KEY": "miosa-tok-placeholder"},
        mcp=[{"name": "refero", "url": "https://api.refero.design/mcp"}],
    )

    write_body = json.loads(write_route.calls.last.request.content)
    manifest = json.loads(write_body["content"])
    exec_body = json.loads(exec_route.calls.last.request.content)

    assert write_body["path"] == "/workspace/.miosa/runtime-bootstrap.json"
    assert manifest["runtime"] == "claude-code"
    assert manifest["connectors"] == ["anthropic/workspace-claude"]
    assert manifest["env"] == {"ANTHROPIC_API_KEY": "miosa-tok-placeholder"}
    assert exec_body["cwd"] == "/workspace"
    assert "runtime available" in exec_body["command"]
    assert result["ok"] is True
    assert result["manifest_path"] == "/workspace/.miosa/runtime-bootstrap.json"


def test_devices_bootstrap_accepts_managed_connector_bindings(mock_api, client):
    write_route = mock_api.post("/devices/comp_123/files/write").respond(
        200, json={"data": {"path": "/workspace/.miosa/runtime-bootstrap.json"}}
    )
    mock_api.post("/devices/comp_123/exec").respond(
        200, json={"data": {"exit_code": 0, "stdout": "runtime available\n"}}
    )

    client.devices.bootstrap(
        "comp_123",
        runtime="claude-code",
        connectors=[
            {
                "uid": "refero",
                "type": "mcp",
                "managed": True,
                "server_url": "https://api.refero.design/mcp",
            },
            "anthropic/cliniciq",
        ],
        env={"ANTHROPIC_API_KEY": "miosa-managed:anthropic/cliniciq"},
    )

    write_body = json.loads(write_route.calls.last.request.content)
    manifest = json.loads(write_body["content"])

    assert manifest["connectors"] == [
        {
            "uid": "refero",
            "type": "mcp",
            "managed": True,
            "server_url": "https://api.refero.design/mcp",
        },
        "anthropic/cliniciq",
    ]
    assert manifest["env"] == {
        "ANTHROPIC_API_KEY": "miosa-managed:anthropic/cliniciq"
    }


def test_devices_browser(mock_api, client):
    route = mock_api.get("/devices/comp_123/browser").respond(
        200,
        json={
            "data": {
                "kind": "computer_browser",
                "desktop_url": "https://desktop.example.test",
                "ws_url": "wss://desktop.example.test/vnc/websockify",
            }
        },
    )

    result = client.devices.browser("comp_123")

    assert route.called
    assert result["kind"] == "computer_browser"
    assert "desktop" in result["desktop_url"]
