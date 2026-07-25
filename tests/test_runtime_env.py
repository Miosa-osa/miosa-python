def test_runtime_env_crud(mock_api, client):
    create = mock_api.post("/runtime-env").respond(
        201,
        json={
            "data": {
                "id": "env_123",
                "scope": "workspace",
                "workspace_id": "workspace_1",
                "target": "deployment",
                "name": "ANTHROPIC_API_KEY",
                "preview": "sk-ant...test",
            }
        },
    )
    mock_api.get("/runtime-env").respond(
        200,
        json={
            "data": [
                {
                    "id": "env_123",
                    "scope": "workspace",
                    "workspace_id": "workspace_1",
                    "target": "deployment",
                    "name": "ANTHROPIC_API_KEY",
                }
            ]
        },
    )
    mock_api.get("/runtime-env/env_123").respond(
        200, json={"data": {"id": "env_123", "name": "ANTHROPIC_API_KEY"}}
    )
    delete = mock_api.delete("/runtime-env/env_123").respond(204)

    env = client.runtime_env.set(
        scope="workspace",
        workspaceId="workspace_1",
        target="deployment",
        name="ANTHROPIC_API_KEY",
        value="sk-ant-test",
        metadata={"provider": "anthropic"},
    )
    listed = client.runtime_env.list(
        scope="workspace", workspace_id="workspace_1", target="deployment"
    )
    fetched = client.runtime_env.get("env_123")
    client.runtime_env.delete("env_123")

    assert env["id"] == "env_123"
    assert listed[0]["target"] == "deployment"
    assert fetched["name"] == "ANTHROPIC_API_KEY"
    assert b"workspace_id" in create.calls.last.request.content
    assert b"metadata" in create.calls.last.request.content
    assert "scope=workspace" in str(mock_api.calls[1].request.url)
    assert "workspace_id=workspace_1" in str(mock_api.calls[1].request.url)
    assert "target=deployment" in str(mock_api.calls[1].request.url)
    assert delete.called
