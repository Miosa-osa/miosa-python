def test_agent_runtime_profiles_crud(mock_api, client):
    create = mock_api.post("/agent-runtime-profiles").respond(
        201,
        json={
            "data": {
                "id": "arp_123",
                "workspace_id": "workspace_1",
                "project_id": "project_1",
                "name": "Claude builder",
                "runtime": "claude-code",
                "applies_to": {"sandboxes": True},
                "is_default": True,
            }
        },
    )
    mock_api.get("/agent-runtime-profiles").respond(
        200,
        json={
            "data": [
                {
                    "id": "arp_123",
                    "name": "Claude builder",
                    "runtime": "claude-code",
                }
            ]
        },
    )
    mock_api.get("/agent-runtime-profiles/arp_123").respond(
        200, json={"data": {"id": "arp_123", "runtime": "claude-code"}}
    )
    update = mock_api.put("/agent-runtime-profiles/arp_123").respond(
        200, json={"data": {"id": "arp_123", "runtime": "codex"}}
    )
    delete = mock_api.delete("/agent-runtime-profiles/arp_123").respond(204)

    profile = client.agent_runtime_profiles.create(
        workspaceId="workspace_1",
        projectId="project_1",
        name="Claude builder",
        runtime="claude-code",
        appliesTo={"sandboxes": True},
        isDefault=True,
    )
    listed = client.agent_runtime_profiles.list(workspace_id="workspace_1", project_id="project_1")
    fetched = client.agent_runtime_profiles.get("arp_123")
    updated = client.agent_runtime_profiles.update("arp_123", runtime="codex")
    client.agent_runtime_profiles.delete("arp_123")

    assert profile["id"] == "arp_123"
    assert listed[0]["id"] == "arp_123"
    assert fetched["runtime"] == "claude-code"
    assert updated["runtime"] == "codex"
    assert b"workspace_id" in create.calls.last.request.content
    assert b"project_id" in create.calls.last.request.content
    assert "workspace_id=workspace_1" in str(mock_api.calls[1].request.url)
    assert "project_id=project_1" in str(mock_api.calls[1].request.url)
    assert b"runtime" in update.calls.last.request.content
    assert delete.called


def test_agent_runtime_profiles_accepts_managed_connector_bindings(mock_api, client):
    create = mock_api.post("/agent-runtime-profiles").respond(
        201,
        json={
            "data": {
                "id": "arp_clinic",
                "workspace_id": "clinic_workspace",
                "name": "ClinicIQ Claude Code",
                "runtime": "claude-code",
                "connectors": [
                    {
                        "uid": "refero",
                        "type": "mcp",
                        "managed": True,
                        "server_url": "https://api.refero.design/mcp",
                    }
                ],
            }
        },
    )

    profile = client.agent_runtime_profiles.create(
        workspaceId="clinic_workspace",
        name="ClinicIQ Claude Code",
        runtime="claude-code",
        connectors=[
            {
                "uid": "refero",
                "type": "mcp",
                "managed": True,
                "server_url": "https://api.refero.design/mcp",
            }
        ],
        env={"ANTHROPIC_API_KEY": "miosa-managed:anthropic/cliniciq"},
        metadata={"model": "claude-opus-4.8", "white_label_client": "cliniciq"},
    )

    body = create.calls.last.request.content

    assert profile["id"] == "arp_clinic"
    assert b'"workspace_id":"clinic_workspace"' in body
    assert b'"runtime":"claude-code"' in body
    assert b'"uid":"refero"' in body
    assert b'"managed":true' in body
    assert b'"ANTHROPIC_API_KEY":"miosa-managed:anthropic/cliniciq"' in body
