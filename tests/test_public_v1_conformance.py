from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

EXPECTED_CONTRACT_VERSION = "1.0.0"
EXPECTED_CONTRACT_COMMIT = "774abcbc97380b599009759632691dc60d8e6b38"


def contracts_root() -> Path:
    configured = os.environ.get("MIOSA_API_CONTRACTS_ROOT")
    root = (
        Path(configured).expanduser().resolve()
        if configured
        else Path(__file__).resolve().parents[2] / "contract-fixtures" / "public-v1"
    )
    try:
        if configured:
            openapi_path = root / "openapi" / "public-v1.yaml"
            contract = yaml.safe_load(openapi_path.read_text())
            actual_version = contract.get("info", {}).get("version")
        else:
            actual_version = (root / "CONTRACT_VERSION").read_text().strip()
            actual_commit = (root / "CONTRACT_COMMIT").read_text().strip()
            if actual_commit != EXPECTED_CONTRACT_COMMIT:
                raise ValueError(f"found contract commit {actual_commit}")
        if actual_version != EXPECTED_CONTRACT_VERSION:
            raise ValueError(f"found OpenAPI version {actual_version!r}")
    except Exception as exc:
        raise RuntimeError(
            "MIOSA API contracts unavailable or incompatible: "
            f"resolved root={root}; expected public-v1 version="
            f"{EXPECTED_CONTRACT_VERSION}; expected commit={EXPECTED_CONTRACT_COMMIT}; "
            f"{exc}"
        ) from exc
    return root


def fixture(name: str) -> dict[str, Any]:
    root = contracts_root()
    path = root / "fixtures" / "conformance" / f"{name}.yaml"
    try:
        return yaml.safe_load(path.read_text())
    except Exception as exc:
        raise RuntimeError(
            f"Cannot load conformance fixture {path}; resolved root={root}; "
            f"expected public-v1 version={EXPECTED_CONTRACT_VERSION}; "
            f"expected commit={EXPECTED_CONTRACT_COMMIT}; {exc}"
        ) from exc


def test_default_small_create_fixture(mock_api, client):
    create = fixture("create-default-small-request")
    sandbox_response = fixture("sandbox-response")
    response_body = {
        **sandbox_response["body"],
        "tenant_id": "tenant_123",
        "owner_id": "user_123",
        "workspace_id": "workspace_123",
        "project_id": "project_123",
    }
    route = mock_api.post(create["path"]).respond(201, json=response_body)

    sandbox = client.sandboxes.create(opts=create["body"])

    assert json.loads(route.calls.last.request.content) == create["body"]
    assert sandbox.resource_contract == sandbox_response["body"]["resource_contract"]
    assert sandbox.tenant_id == "tenant_123"
    assert sandbox.owner_id == "user_123"
    assert sandbox.workspace_id == "workspace_123"
    assert sandbox.project_id == "project_123"
    assert sandbox.timeout_remaining_ms == 3_599_000
    assert sandbox.idle_timeout_sec == 0


def test_pause_and_usage_fixtures_preserve_sandbox_fields(mock_api, client):
    sandbox_response = fixture("sandbox-response")
    pause_response = fixture("pause-response")
    usage_response = fixture("usage-response")
    sandbox_id = sandbox_response["body"]["id"]
    mock_api.get(f"/sandboxes/{sandbox_id}").respond(json=sandbox_response["body"])
    mock_api.post(f"/sandboxes/{sandbox_id}/pause").respond(json=pause_response["body"])
    mock_api.get(f"/sandboxes/{sandbox_id}/usage").respond(json=usage_response["body"])

    sandbox = client.sandboxes.get(sandbox_id)
    sandbox.pause()

    assert sandbox.state == "paused"
    assert sandbox.resource_contract == sandbox_response["body"]["resource_contract"]
    assert sandbox.usage() == usage_response["body"]["data"]


def test_templates_fixture_uses_top_level_catalog(mock_api, client):
    templates = fixture("templates-response")
    mock_api.get(templates["path"]).respond(json=templates["body"])

    catalog = client.templates.catalog()

    assert catalog["templates"] == templates["body"]["templates"]
    assert catalog["shape_contracts"] == templates["body"]["shape_contracts"]
