from __future__ import annotations

import httpx


def test_runs_dispatches_sandbox_instruction(mock_api, client):
    route = mock_api.post("/runs").respond(
        200,
        json={
            "data": {
                "id": "run_1",
                "target_kind": "sandbox",
                "target_id": "sbx_1",
                "runner": "claude",
                "instruction": "build it",
                "status": "succeeded",
            }
        },
    )

    result = client.runs.run(
        sandbox_id="sbx_1",
        target_kind="sandbox",
        runner="claude-code",
        cwd="/workspace",
        timeout=1800,
        wait=False,
        env={"FEATURE_FLAG": "on"},
        agent_runtime_profile_id="profile_1",
        external_workspace_id="clinic-iq",
        external_user_id="founder-1",
        external_project_id="landing-page",
        execution_packet={"goal": "build landing page", "context": {"customer": "ClinicIQ"}},
        expected_outputs={"files": [{"path": "/workspace/report.html", "kind": "html"}]},
        approval_policy={"publish": "manual"},
        capability_requirements=["filesystem", "shell", "files", "downloads"],
        instruction="build it",
        runtime_id="sbx_1",
    )

    assert route.called
    assert "idempotency-key" not in route.calls.last.request.headers
    assert route.calls.last.request.content
    assert b'"agent_runtime_profile_id":"profile_1"' in route.calls.last.request.content
    assert b'"wait":false' in route.calls.last.request.content
    assert b'"external_workspace_id":"clinic-iq"' in route.calls.last.request.content
    assert b'"external_user_id":"founder-1"' in route.calls.last.request.content
    assert b'"external_project_id":"landing-page"' in route.calls.last.request.content
    assert b'"FEATURE_FLAG":"on"' in route.calls.last.request.content
    assert b'"execution_packet":{"goal":"build landing page"' in route.calls.last.request.content
    assert (
        b'"expected_outputs":{"files":[{"path":"/workspace/report.html"'
        in route.calls.last.request.content
    )
    assert b'"approval_policy":{"publish":"manual"}' in route.calls.last.request.content
    assert (
        b'"capability_requirements":["filesystem","shell","files","downloads"]'
        in route.calls.last.request.content
    )
    assert result["id"] == "run_1"


def test_runs_dispatches_with_idempotency_key(mock_api, client):
    route = mock_api.post("/runs").respond(
        200,
        json={"data": {"id": "run_1", "status": "running"}},
    )

    result = client.runs.run(
        sandbox_id="sbx_1",
        instruction="build it",
        idempotency_key="clinic-iq-run-123",
    )

    assert route.calls.last.request.headers["idempotency-key"] == "clinic-iq-run-123"
    assert result["id"] == "run_1"


def test_runs_list_get_and_cancel(mock_api, client):
    list_route = mock_api.get("/runs").respond(
        200,
        json={
            "data": [
                {
                    "id": "run_1",
                    "target_kind": "sandbox",
                    "target_id": "sbx_1",
                    "runner": "codex",
                    "instruction": "build it",
                    "status": "running",
                }
            ]
        },
    )
    mock_api.get("/runs/run_1").respond(
        200,
        json={
            "data": {
                "id": "run_1",
                "target_kind": "sandbox",
                "target_id": "sbx_1",
                "runner": "codex",
                "instruction": "build it",
                "status": "running",
            }
        },
    )
    cancel_route = mock_api.post("/runs/run_1/cancel").respond(
        200,
        json={
            "data": {
                "id": "run_1",
                "target_kind": "sandbox",
                "target_id": "sbx_1",
                "runner": "codex",
                "instruction": "build it",
                "status": "canceled",
            }
        },
    )

    listed = client.runs.list(
        sandbox_id="sbx_1",
        status="running",
        external_workspace_id="clinic-iq",
        external_user_id="founder-1",
        external_project_id="landing-page",
    )
    fetched = client.runs.get("run_1")
    canceled = client.runs.cancel("run_1")

    assert list_route.called
    assert "sandbox_id=sbx_1" in str(list_route.calls.last.request.url)
    assert "status=running" in str(list_route.calls.last.request.url)
    assert "external_workspace_id=clinic-iq" in str(list_route.calls.last.request.url)
    assert "external_user_id=founder-1" in str(list_route.calls.last.request.url)
    assert "external_project_id=landing-page" in str(list_route.calls.last.request.url)
    assert listed[0]["id"] == "run_1"
    assert fetched["id"] == "run_1"
    assert canceled["status"] == "canceled"
    assert cancel_route.called


def test_runs_lists_and_downloads_files(mock_api, client):
    files_route = mock_api.get("/runs/run_1/files").respond(
        200,
        json={
            "data": [
                {
                    "id": "file_1",
                    "path": "/workspace/report.html",
                    "kind": "html",
                    "mime_type": "text/html",
                }
            ]
        },
    )
    download_route = mock_api.get(
        "/runs/run_1/files/file_1/download?disposition=inline"
    ).respond(
        200,
        content=b"<html>report</html>",
        headers={"content-type": "text/html"},
    )

    files = client.runs.files("run_1")
    content = client.runs.download_file("run_1", "file_1", inline=True)

    assert files_route.called
    assert download_route.called
    assert files[0]["id"] == "file_1"
    assert content == b"<html>report</html>"


def test_runs_reads_outputs_files_and_file_downloads(mock_api, client):
    outputs_route = mock_api.get("/runs/run_1/outputs").respond(
        200,
        json={
            "data": {
                "run_id": "run_1",
                "status": "succeeded",
                "result": {"type": "message", "id": "run_1:result", "text": "done"},
                "message": "done",
                "messages": [],
                "command_output": {"stdout": "done", "stderr": "", "exit_code": 0},
                "activity": [],
                "files": [{"id": "file_1", "path": "/workspace/report.html", "kind": "html"}],
                "downloads": [],
                "previews": [],
                "diagnostics": [],
            }
        },
    )
    files_route = mock_api.get("/runs/run_1/files").respond(
        200,
        json={
            "data": [
                {"id": "file_1", "path": "/workspace/report.html", "kind": "html"}
            ]
        },
    )
    download_route = mock_api.get(
        "/runs/run_1/files/file_1/download?disposition=inline"
    ).respond(
        200,
        content=b"<html>report</html>",
        headers={"content-type": "text/html"},
    )

    outputs = client.runs.outputs("run_1")
    files = client.runs.files("run_1")
    content = client.runs.download_file("run_1", "file_1", inline=True)

    assert outputs_route.called
    assert files_route.called
    assert download_route.called
    assert outputs["result"] == {"type": "message", "id": "run_1:result", "text": "done"}
    assert files[0]["id"] == "file_1"
    assert content == b"<html>report</html>"


def test_runs_lists_activity(mock_api, client):
    activity_route = mock_api.get("/runs/run_1/activity").respond(
        200,
        json={
            "data": [
                {
                    "id": "evt_1",
                    "run_id": "run_1",
                    "sequence": 1,
                    "type": "created",
                    "message": "Run created",
                }
            ]
        },
    )

    activity = client.runs.activity("run_1")

    assert activity_route.called
    assert activity[0]["id"] == "evt_1"
    assert activity[0]["type"] == "created"


def test_runs_lists_events_with_cursor_and_limit(mock_api, client):
    events_route = mock_api.get("/runs/run_1/events?after_id=evt_1&limit=50").respond(
        200,
        json={
            "data": {
                "events": [
                    {
                        "id": "evt_2",
                        "run_id": "run_1",
                        "type": "assistant.message",
                        "metadata": {"text": "done"},
                    }
                ]
            }
        },
    )

    events = client.runs.events("run_1", after_id="evt_1", limit=50)

    assert events_route.called
    assert events[0]["id"] == "evt_2"
    assert events[0]["metadata"] == {"text": "done"}


def test_runs_reads_command_output(mock_api, client):
    route = mock_api.get("/runs/run_1/command-output").respond(
        200,
        json={"data": {"stdout": "done", "stderr": "", "exit_code": 0}},
    )

    output = client.runs.command_output("run_1")

    assert route.called
    assert output == {"stdout": "done", "stderr": "", "exit_code": 0}


def test_runs_waits_for_completion(mock_api, client):
    route = mock_api.get("/runs/run_1")
    route.side_effect = [
        httpx.Response(200, json={"data": {"id": "run_1", "status": "running"}}),
        httpx.Response(200, json={"data": {"id": "run_1", "status": "succeeded"}}),
    ]

    result = client.runs.wait_for_completion(
        "run_1", timeout=1.0, poll_interval=0.0
    )

    assert route.called
    assert len(route.calls) == 2
    assert result["status"] == "succeeded"


def test_runs_preserves_reserved_computer_target_fields(mock_api, client):
    route = mock_api.post("/runs").respond(
        200,
        json={
            "data": {
                "id": "run_2",
                "target_kind": "computer",
                "target_id": "cmp_1",
                "runner": "codex",
                "instruction": "test the browser",
                "status": "failed",
            }
        },
    )

    client.runs.run(
        computer_id="cmp_1",
        target_kind="computer",
        runner="codex",
        instruction="test the browser",
    )

    assert route.called
    assert b'"computer_id":"cmp_1"' in route.calls.last.request.content


def test_sandbox_run_dispatches_default_claude_code(mock_api, client):
    mock_api.get("/sandboxes/sbx_1").respond(
        200,
        json={"data": {"id": "sbx_1", "state": "running", "ready": True}},
    )
    route = mock_api.post("/runs").respond(
        200,
        json={
            "data": {
                "id": "run_sbx",
                "target_kind": "sandbox",
                "target_id": "sbx_1",
                "runner": "claude",
                "instruction": "build it",
                "status": "succeeded",
            }
        },
    )

    sandbox = client.sandboxes.get("sbx_1")
    run = sandbox.run_agent("build it")

    assert route.called
    assert b'"target_kind":"sandbox"' in route.calls.last.request.content
    assert b'"sandbox_id":"sbx_1"' in route.calls.last.request.content
    assert b'"runner":"claude-code"' in route.calls.last.request.content
    assert b'"cwd":"/workspace"' in route.calls.last.request.content
    assert b'"wait":true' in route.calls.last.request.content
    assert run["id"] == "run_sbx"


def test_computer_run_dispatches_codex_with_env(mock_api, client):
    mock_api.get("/computers/cmp_1").respond(
        200,
        json={
            "id": "cmp_1",
            "name": "builder",
            "status": "running",
            "template_type": "miosa-desktop",
        },
    )
    route = mock_api.post("/runs").respond(
        200,
        json={
            "data": {
                "id": "run_cmp",
                "target_kind": "computer",
                "target_id": "cmp_1",
                "runner": "codex",
                "instruction": "inspect desktop files",
                "status": "running",
            }
        },
    )

    computer = client.computers.get("cmp_1")
    run = computer.run_agent(
        "inspect desktop files",
        runner="codex",
        wait=False,
        env={"CODEX_API_KEY": "redacted"},
    )

    assert route.called
    assert b'"target_kind":"computer"' in route.calls.last.request.content
    assert b'"computer_id":"cmp_1"' in route.calls.last.request.content
    assert b'"runner":"codex"' in route.calls.last.request.content
    assert b'"CODEX_API_KEY":"redacted"' in route.calls.last.request.content
    assert b'"wait":false' in route.calls.last.request.content
    assert run["id"] == "run_cmp"


async def test_async_runs_dispatches_with_idempotency_key(mock_api, async_client):
    route = mock_api.post("/runs").respond(
        200,
        json={"data": {"id": "run_1", "status": "running"}},
    )

    try:
        result = await async_client.runs.run(
            sandbox_id="sbx_1",
            instruction="build it",
            idempotency_key="clinic-iq-run-123",
        )
    finally:
        await async_client.close()

    assert route.calls.last.request.headers["idempotency-key"] == "clinic-iq-run-123"
    assert result["id"] == "run_1"


async def test_async_runs_lists_events_with_cursor_and_limit(mock_api, async_client):
    events_route = mock_api.get("/runs/run_1/events?after_id=evt_1&limit=50").respond(
        200,
        json={
            "data": [
                {
                    "id": "evt_2",
                    "run_id": "run_1",
                    "type": "run.succeeded",
                    "status": "succeeded",
                    "metadata": {},
                }
            ]
        },
    )

    try:
        events = await async_client.runs.events("run_1", after_id="evt_1", limit=50)
    finally:
        await async_client.close()

    assert events_route.called
    assert events[0]["id"] == "evt_2"
    assert events[0]["status"] == "succeeded"
