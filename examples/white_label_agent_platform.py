"""White-label agent platform flow.

Your application does planning and context assembly. MIOSA devices do isolated
filesystem/command work, while Connect injects provider credentials into the
runtime without returning raw secrets to the app.

Required env:
    MIOSA_API_KEY
    MIOSA_WORKSPACE_ID
    MIOSA_EXTERNAL_WORKSPACE_ID
    ANTHROPIC_API_KEY
"""

from __future__ import annotations

import os

from miosa import Miosa


def required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


client = Miosa(api_key=required("MIOSA_API_KEY"))
workspace_id = required("MIOSA_WORKSPACE_ID")
external_workspace_id = os.environ.get(
    "MIOSA_EXTERNAL_WORKSPACE_ID", "clinic-iq-workspace"
)


def main() -> None:
    connector = client.connectors.create(
        "anthropic",
        name="clinic-iq-claude",
        scope="workspace",
        workspace_id=workspace_id,
        external_workspace_id=external_workspace_id,
        value=required("ANTHROPIC_API_KEY"),
    )

    sandbox = client.sandboxes.create(
        template_id="nextjs",
        name="clinic-iq-builder",
        timeout_sec=3600,
    )
    sandbox_id = sandbox.id
    connector_uid = connector.get("uid", "anthropic/clinic-iq-claude")

    client.connectors.create_default(
        connector=connector_uid,
        workspace_id=workspace_id,
        external_workspace_id=external_workspace_id,
        default_scope="external_workspace",
        target="agent",
        mode="brokered-env",
        allowed_scopes=["messages:create"],
    )

    client.connectors.materialize_defaults(
        workspace_id=workspace_id,
        resource_type="sandbox",
        resource_id=sandbox_id,
        target="agent",
        external_workspace_id=external_workspace_id,
    )

    client.devices.write_file(
        sandbox_id,
        "/workspace/PLAN.md",
        content="\n".join(
            [
                "# Clinic IQ landing page",
                "",
                "Build a polished landing page for a white-label healthcare AI product.",
                "Use the customer profile and output all artifacts under /workspace/out.",
            ]
        ),
    )

    result = client.devices.exec(
        sandbox_id,
        "npm install && npm run build",
        cwd="/workspace",
        timeout_ms=10 * 60 * 1000,
    )
    print(result)

    artifact = client.devices.read_file(sandbox_id, "/workspace/PLAN.md")
    print(
        {
            "artifact": artifact["path"],
            "encoding": artifact["encoding"],
            "bytes": artifact.get("size"),
        }
    )


if __name__ == "__main__":
    main()
