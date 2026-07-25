from __future__ import annotations

import httpx


def test_agent_run_groups_lifecycle(mock_api, client):
    create = mock_api.post("/agent-run-groups").respond(
        201, json={"data": {"id": "grp_1", "name": "fanout", "status": "running"}}
    )
    list_route = mock_api.get("/agent-run-groups").respond(
        200, json={"data": [{"id": "grp_1", "name": "fanout", "status": "running"}]}
    )
    get_route = mock_api.get("/agent-run-groups/grp_1?include=runs").respond(
        200, json={"data": {"id": "grp_1", "name": "fanout", "runs": []}}
    )
    dispatch = mock_api.post("/agent-run-groups/grp_1/dispatch").respond(
        200,
        json={
            "data": {
                "group": {"id": "grp_1", "name": "fanout", "status": "succeeded"},
                "results": [{"index": 0, "ok": True, "run": {"id": "run_1"}}],
            }
        },
    )
    cancel = mock_api.post("/agent-run-groups/grp_1/cancel").respond(
        200, json={"data": {"id": "grp_1", "name": "fanout", "status": "canceled"}}
    )
    events_route = mock_api.get("/agent-run-groups/grp_1/events").respond(
        200,
        json={
            "data": [
                {
                    "id": "evt_1",
                    "agent_run_group_id": "grp_1",
                    "agent_run_id": "run_1",
                    "type": "created",
                }
            ]
        },
    )
    artifacts_group_route = mock_api.get("/agent-run-groups/grp_1?include=runs").respond(
        200,
        json={
            "data": {
                "id": "grp_1",
                "name": "fanout",
                "status": "succeeded",
                "runs": [{"id": "run_1", "status": "succeeded"}],
            }
        },
    )
    artifacts_route = mock_api.get("/agent-runs/run_1/artifacts").respond(
        200,
        json={
            "data": [
                {
                    "id": "art_1",
                    "path": "/workspace/report.html",
                    "kind": "html",
                }
            ]
        },
    )

    created = client.agent_run_groups.create(
        name="fanout", workspace_id="wk_1", concurrency_limit=10
    )
    listed = client.agent_run_groups.list(workspace_id="wk_1", status="running", limit=20)
    fetched = client.agent_run_groups.get("grp_1", include_runs=True)
    dispatched = client.agent_run_groups.dispatch(
        "grp_1",
        [
            {
                "sandbox_id": "sbx_1",
                "provider": "claude",
                "prompt": "build",
                "orchestration_role": "worker",
                "skip_agent_runtime_profile": False,
                "execution_packet": {"goal": "build workspace"},
                "output_contract": {"artifacts": ["/workspace/report.html"]},
                "approval_policy": {"publish": "manual"},
                "capability_requirements": ["filesystem"],
            }
        ],
    )
    client.agent_run_groups.dispatch(
        "grp_1",
        [{"sandbox_id": "sbx_2", "provider": "codex", "prompt": "test"}],
        async_=True,
    )
    canceled = client.agent_run_groups.cancel("grp_1")
    events = client.agent_run_groups.events("grp_1")
    artifacts = client.agent_run_groups.artifacts("grp_1")

    assert create.called
    assert b'"workspace_id":"wk_1"' in create.calls.last.request.content
    assert b'"concurrency_limit":10' in create.calls.last.request.content
    assert list_route.called
    assert "workspace_id=wk_1" in str(list_route.calls.last.request.url)
    assert "status=running" in str(list_route.calls.last.request.url)
    assert get_route.called
    assert dispatch.called
    assert len(dispatch.calls) == 2
    first_dispatch_body = dispatch.calls[0].request.content
    second_dispatch_body = dispatch.calls[1].request.content
    assert b'"orchestration_role":"worker"' in first_dispatch_body
    assert b'"skip_agent_runtime_profile":false' in first_dispatch_body
    assert b'"execution_packet":{"goal":"build workspace"}' in first_dispatch_body
    assert b'"output_contract":{"artifacts":["/workspace/report.html"]}' in first_dispatch_body
    assert b'"approval_policy":{"publish":"manual"}' in first_dispatch_body
    assert b'"capability_requirements":["filesystem"]' in first_dispatch_body
    assert b'"async":true' in second_dispatch_body
    assert cancel.called
    assert events_route.called
    assert artifacts_group_route.called
    assert artifacts_route.called
    assert created["id"] == "grp_1"
    assert listed[0]["id"] == "grp_1"
    assert fetched["id"] == "grp_1"
    assert "results" in dispatched
    assert canceled["status"] == "canceled"
    assert events[0]["agent_run_id"] == "run_1"
    assert artifacts[0]["agent_run_id"] == "run_1"
    assert artifacts[0]["path"] == "/workspace/report.html"


def test_agent_run_groups_waits_for_completion(mock_api, client):
    route = mock_api.get("/agent-run-groups/grp_1?include=runs")
    route.side_effect = [
        httpx.Response(200, json={"data": {"id": "grp_1", "status": "running"}}),
        httpx.Response(
            200,
            json={"data": {"id": "grp_1", "status": "succeeded", "runs": []}},
        ),
    ]

    result = client.agent_run_groups.wait_for_completion(
        "grp_1", timeout=1.0, poll_interval=0.0, include_runs=True
    )

    assert route.called
    assert len(route.calls) == 2
    assert result["status"] == "succeeded"
