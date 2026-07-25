"""Canonical ownership arguments for sandbox creation."""

from __future__ import annotations

import json
from typing import Any

from miosa.resources.sandboxes import CreateSandboxOptions

from .conftest import SANDBOX_JSON

OWNERSHIP = {
    "workspace_id": "ws_123",
    "workspace_slug": "clinic-iq",
    "workspace_name": "Clinic IQ",
    "project_id": "prj_123",
    "project_slug": "patient-portal",
    "project_name": "Patient Portal",
}


def test_sync_create_sends_canonical_ownership_arguments(mock_api: Any, client: Any) -> None:
    route = mock_api.post("/sandboxes").respond(200, json={"data": SANDBOX_JSON})

    client.sandboxes.create(
        workspace_id=OWNERSHIP["workspace_id"],
        workspace_slug=OWNERSHIP["workspace_slug"],
        workspace_name=OWNERSHIP["workspace_name"],
        project_id=OWNERSHIP["project_id"],
        project_slug=OWNERSHIP["project_slug"],
        project_name=OWNERSHIP["project_name"],
    )

    body = json.loads(route.calls.last.request.content)
    assert {key: body[key] for key in OWNERSHIP} == OWNERSHIP


async def test_async_create_merges_and_sends_typed_canonical_ownership_options(
    mock_api: Any, async_client: Any
) -> None:
    route = mock_api.post("/sandboxes").respond(200, json={"data": SANDBOX_JSON})
    opts: CreateSandboxOptions = {
        "workspace_id": "ws_123",
        "workspace_slug": "clinic-iq",
        "workspace_name": "Stale workspace name",
        "project_id": "prj_123",
        "project_slug": "patient-portal",
        "project_name": "Stale project name",
    }

    await async_client.sandboxes.create(
        opts=opts,
        workspace_name=OWNERSHIP["workspace_name"],
        project_name=OWNERSHIP["project_name"],
    )

    body = json.loads(route.calls.last.request.content)
    assert {key: body[key] for key in OWNERSHIP} == OWNERSHIP
    await async_client.close()
