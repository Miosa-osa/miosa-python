from __future__ import annotations

import httpx


def test_agent_runs_dispatches_sandbox_prompt(mock_api, client):
    route = mock_api.post("/agent-runs").respond(
        200,
        json={
            "data": {
                "id": "run_1",
                "target_kind": "sandbox",
                "target_id": "sbx_1",
        "provider": "claude",
                "prompt": "build it",
                "status": "succeeded",
            }
        },
    )

    result = client.agent_runs.run(
        sandbox_id="sbx_1",
        target_kind="sandbox",
        provider="claude-code",
        cwd="/workspace",
        timeout=1800,
        wait=False,
        env={"FEATURE_FLAG": "on"},
        agent_runtime_profile_id="profile_1",
        external_workspace_id="clinic-iq",
        external_user_id="founder-1",
        external_project_id="landing-page",
        execution_packet={"goal": "build landing page", "context": {"customer": "ClinicIQ"}},
        output_contract={
            "artifacts": [{"path": "/workspace/report.html", "kind": "html"}],
            "preview_port": 3000,
        },
        approval_policy={"publish": "manual"},
        capability_requirements=["filesystem", "shell", "artifact_downloads"],
        output_format="stream-json",
        resume_session_id="sess_123",
        json=True,
        output_schema="/workspace/schema.json",
        image="/workspace/mockup.png",
        prompt="build it",
    )

    assert route.called
    assert route.calls.last.request.content
    assert b'"agent_runtime_profile_id":"profile_1"' in route.calls.last.request.content
    assert b'"wait":false' in route.calls.last.request.content
    assert b'"external_workspace_id":"clinic-iq"' in route.calls.last.request.content
    assert b'"external_user_id":"founder-1"' in route.calls.last.request.content
    assert b'"external_project_id":"landing-page"' in route.calls.last.request.content
    assert b'"FEATURE_FLAG":"on"' in route.calls.last.request.content
    assert b'"execution_packet":{"goal":"build landing page"' in route.calls.last.request.content
    assert (
        b'"output_contract":{"artifacts":[{"path":"/workspace/report.html"'
        in route.calls.last.request.content
    )
    assert b'"approval_policy":{"publish":"manual"}' in route.calls.last.request.content
    assert (
        b'"capability_requirements":["filesystem","shell","artifact_downloads"]'
        in route.calls.last.request.content
    )
    assert b'"output_format":"stream-json"' in route.calls.last.request.content
    assert b'"resume_session_id":"sess_123"' in route.calls.last.request.content
    assert b'"json":true' in route.calls.last.request.content
    assert b'"output_schema":"/workspace/schema.json"' in route.calls.last.request.content
    assert b'"image":"/workspace/mockup.png"' in route.calls.last.request.content
    assert result["id"] == "run_1"


def test_agent_runs_list_get_and_cancel(mock_api, client):
    list_route = mock_api.get("/agent-runs").respond(
        200,
        json={
            "data": [
                {
                    "id": "run_1",
                    "target_kind": "sandbox",
                    "target_id": "sbx_1",
                    "provider": "codex",
                    "prompt": "build it",
                    "status": "running",
                }
            ]
        },
    )
    mock_api.get("/agent-runs/run_1").respond(
        200,
        json={
            "data": {
                "id": "run_1",
                "target_kind": "sandbox",
                "target_id": "sbx_1",
                "provider": "codex",
                "prompt": "build it",
                "status": "running",
            }
        },
    )
    cancel_route = mock_api.post("/agent-runs/run_1/cancel").respond(
        200,
        json={
            "data": {
                "id": "run_1",
                "target_kind": "sandbox",
                "target_id": "sbx_1",
                "provider": "codex",
                "prompt": "build it",
                "status": "canceled",
            }
        },
    )

    listed = client.agent_runs.list(
        sandbox_id="sbx_1",
        status="running",
        external_workspace_id="clinic-iq",
        external_user_id="founder-1",
        external_project_id="landing-page",
    )
    fetched = client.agent_runs.get("run_1")
    canceled = client.agent_runs.cancel("run_1")

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


def test_agent_runs_lists_and_downloads_artifacts(mock_api, client):
    artifacts_route = mock_api.get("/agent-runs/run_1/artifacts").respond(
        200,
        json={
            "data": [
                {
                    "id": "art_1",
                    "path": "/workspace/report.html",
                    "kind": "html",
                    "mime_type": "text/html",
                }
            ]
        },
    )
    download_route = mock_api.get(
        "/agent-runs/run_1/artifacts/art_1/download?disposition=inline"
    ).respond(
        200,
        content=b"<html>report</html>",
        headers={"content-type": "text/html"},
    )

    artifacts = client.agent_runs.artifacts("run_1")
    content = client.agent_runs.download_artifact("run_1", "art_1", inline=True)

    assert artifacts_route.called
    assert download_route.called
    assert artifacts[0]["id"] == "art_1"
    assert content == b"<html>report</html>"


def test_agent_runs_lists_events(mock_api, client):
    events_route = mock_api.get("/agent-runs/run_1/events").respond(
        200,
        json={
            "data": [
                {
                    "id": "evt_1",
                    "agent_run_id": "run_1",
                    "sequence": 1,
                    "type": "created",
                    "message": "Agent run created",
                }
            ]
        },
    )

    events = client.agent_runs.events("run_1")

    assert events_route.called
    assert events[0]["id"] == "evt_1"
    assert events[0]["type"] == "created"


def test_agent_runs_waits_for_completion(mock_api, client):
    route = mock_api.get("/agent-runs/run_1")
    route.side_effect = [
        httpx.Response(200, json={"data": {"id": "run_1", "status": "running"}}),
        httpx.Response(200, json={"data": {"id": "run_1", "status": "succeeded"}}),
    ]

    result = client.agent_runs.wait_for_completion(
        "run_1", timeout=1.0, poll_interval=0.0
    )

    assert route.called
    assert len(route.calls) == 2
    assert result["status"] == "succeeded"


def test_agent_runs_preserves_reserved_computer_target_fields(mock_api, client):
    route = mock_api.post("/agent-runs").respond(
        200,
        json={
            "data": {
                "id": "run_2",
                "target_kind": "computer",
                "target_id": "cmp_1",
                "provider": "osa",
                "prompt": "test the browser",
                "status": "failed",
            }
        },
    )

    client.agent_runs.run(
        computer_id="cmp_1",
        target_kind="computer",
        provider="osa",
        prompt="test the browser",
    )

    assert route.called
    assert b'"computer_id":"cmp_1"' in route.calls.last.request.content


def test_sandbox_prompt_dispatches_default_claude_code(mock_api, client):
    mock_api.get("/sandboxes/sbx_1").respond(
        200,
        json={"data": {"id": "sbx_1", "state": "running", "ready": True}},
    )
    route = mock_api.post("/agent-runs").respond(
        200,
        json={
            "data": {
                "id": "run_sbx",
                "target_kind": "sandbox",
                "target_id": "sbx_1",
                "provider": "claude",
                "prompt": "build it",
                "status": "succeeded",
            }
        },
    )

    sandbox = client.sandboxes.get("sbx_1")
    run = sandbox.prompt("build it")

    assert route.called
    assert b'"target_kind":"sandbox"' in route.calls.last.request.content
    assert b'"sandbox_id":"sbx_1"' in route.calls.last.request.content
    assert b'"provider":"claude"' in route.calls.last.request.content
    assert b'"cwd":"/workspace"' in route.calls.last.request.content
    assert b'"wait":true' in route.calls.last.request.content
    assert run["id"] == "run_sbx"


def test_sandbox_prompt_passes_advanced_agent_options(mock_api, client):
    mock_api.get("/sandboxes/sbx_1").respond(
        200,
        json={"data": {"id": "sbx_1", "state": "running", "ready": True}},
    )
    route = mock_api.post("/agent-runs").respond(
        200,
        json={
            "data": {
                "id": "run_sbx",
                "target_kind": "sandbox",
                "target_id": "sbx_1",
                "provider": "claude",
                "prompt": "continue",
                "status": "running",
            }
        },
    )

    sandbox = client.sandboxes.get("sbx_1")
    sandbox.prompt(
        "continue",
        output_format="stream-json",
        resume_session_id="sess_123",
        json=True,
        output_schema="/workspace/schema.json",
        image="/workspace/mockup.png",
    )

    assert route.called
    assert b'"output_format":"stream-json"' in route.calls.last.request.content
    assert b'"resume_session_id":"sess_123"' in route.calls.last.request.content
    assert b'"json":true' in route.calls.last.request.content
    assert b'"output_schema":"/workspace/schema.json"' in route.calls.last.request.content
    assert b'"image":"/workspace/mockup.png"' in route.calls.last.request.content


def test_computer_prompt_dispatches_codex_with_env(mock_api, client):
    mock_api.get("/computers/cmp_1").respond(
        200,
        json={
            "id": "cmp_1",
            "name": "builder",
            "status": "running",
            "template_type": "miosa-desktop",
        },
    )
    route = mock_api.post("/agent-runs").respond(
        200,
        json={
            "data": {
                "id": "run_cmp",
                "target_kind": "computer",
                "target_id": "cmp_1",
                "provider": "codex",
                "prompt": "inspect desktop files",
                "status": "running",
            }
        },
    )

    computer = client.computers.get("cmp_1")
    run = computer.prompt(
        "inspect desktop files",
        provider="codex",
        wait=False,
        env={"CODEX_API_KEY": "redacted"},
    )

    assert route.called
    assert b'"target_kind":"computer"' in route.calls.last.request.content
    assert b'"computer_id":"cmp_1"' in route.calls.last.request.content
    assert b'"provider":"codex"' in route.calls.last.request.content
    assert b'"CODEX_API_KEY":"redacted"' in route.calls.last.request.content
    assert b'"wait":false' in route.calls.last.request.content
    assert run["id"] == "run_cmp"
