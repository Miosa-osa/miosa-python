"""End-to-end Python demo: agent builds a static app, previews it, publishes.

Mirrors examples/agent-builds-static-app/agent.ts but in Python — the same
six API calls a Lovable-style platform makes to take an idea to a live URL.

Run modes:
    python examples/agent_builds_static_app.py           # against real backend
    DRY_RUN=1 python examples/agent_builds_static_app.py  # logs requests only

Env vars:
    MIOSA_API_KEY       required unless DRY_RUN=1
    MIOSA_BASE_URL      defaults to http://localhost:4000/api/v1
    EXT_WORKSPACE_ID    defaults to dental-office-123
    EXT_USER_ID         defaults to dr-smith-456
    EXT_PROJECT_ID      defaults to landing-page-789

Backend phase status (2026-05-15):
    Steps 1-5 work today. Step 6 (publish) lands when Phase 2B/3 backend
    pipeline is wired. Until then it falls through to the sandbox-backed
    bridge endpoint (publish_from_sandbox).
"""

from __future__ import annotations

import os
import sys
from typing import Any

# Allow running directly from the sdks/python/ directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from miosa import Miosa  # noqa: E402
from miosa.errors import MiosaError  # noqa: E402


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Smile Dental</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 36rem;
           margin: 4rem auto; padding: 0 1rem; color: #1a1a1a; }
    h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
    p  { line-height: 1.6; color: #444; }
    .cta { display: inline-block; margin-top: 1.5rem; padding: 0.75rem 1.5rem;
           background: #0a84ff; color: white; border-radius: 6px;
           text-decoration: none; font-weight: 500; }
  </style>
</head>
<body>
  <h1>Smile Dental</h1>
  <p>Friendly family dentistry. New patients welcome.</p>
  <a class="cta" href="mailto:hi@smiledental.test">Book an appointment</a>
</body>
</html>
"""


def main() -> None:
    dry_run = bool(os.environ.get("DRY_RUN"))
    api_key = os.environ.get("MIOSA_API_KEY", "msk_dryrun" if dry_run else None)
    if not api_key:
        print("MIOSA_API_KEY is required (or set DRY_RUN=1).", file=sys.stderr)
        sys.exit(1)

    base_url = os.environ.get("MIOSA_BASE_URL", "http://localhost:4000/api/v1")

    ext_workspace = os.environ.get("EXT_WORKSPACE_ID", "dental-office-123")
    ext_user = os.environ.get("EXT_USER_ID", "dr-smith-456")
    ext_project = os.environ.get("EXT_PROJECT_ID", "landing-page-789")

    if dry_run:
        print("DRY_RUN=1 — no HTTP calls, printing intent only.")
        print(f"  base_url            = {base_url}")
        print(f"  external_workspace  = {ext_workspace}")
        print(f"  external_user       = {ext_user}")
        print(f"  external_project    = {ext_project}")
        print("\nThe six calls a Lovable-style platform would make:")
        print("  1. miosa.sandboxes.create(template_id, external_workspace_id, ...)")
        print("  2. sandbox.write_file('/workspace/index.html', INDEX_HTML)")
        print("  3. sandbox.run('python3 -m http.server 3000 --bind 0.0.0.0', detached=True)")
        print("  4. sandbox.previews.create(port=3000, visibility='private')")
        print("  5. sandbox.previews.share(preview.id)")
        print("  6. miosa.deployments.publish_from_sandbox(sandbox.id, kind='static', ...)")
        return

    with Miosa(api_key=api_key, base_url=base_url) as miosa:
        # 1. Create the sandbox with attribution
        print("[1] creating sandbox…", flush=True)
        sandbox = miosa.sandboxes.create(
            template_id="debian-12-sandbox-v8",
            size="small",
            timeout_sec=1800,
            external_workspace_id=ext_workspace,
            external_user_id=ext_user,
            external_project_id=ext_project,
        )
        print(f"     id={sandbox.id}  state={sandbox.status}")

        try:
            # 2. Write the file the agent is "generating"
            print("[2] writing /workspace/index.html …", flush=True)
            sandbox.write_file("/workspace/index.html", INDEX_HTML)

            # 3. Start a dev server
            print("[3] starting python3 -m http.server on :3000 …", flush=True)
            try:
                sandbox.run(
                    "python3 -m http.server 3000 --bind 0.0.0.0",
                    opts={"working_dir": "/workspace", "timeout_sec": 5},
                )
            except MiosaError as err:
                # detached server doesn't return cleanly; this is expected
                print(f"     (detached: {err})")

            # 4. Create a preview
            print("[4] creating preview on port 3000 …", flush=True)
            preview_resource: Any = sandbox.previews  # type: ignore[attr-defined]
            preview = preview_resource.create(port=3000, visibility="private")
            preview_url = preview.get("url") if isinstance(preview, dict) else preview
            print(f"     preview url={preview_url}")

            # 5. Mint a share token (safe for browser)
            print("[5] minting share token …", flush=True)
            try:
                share = preview_resource.share(preview["id"] if isinstance(preview, dict) else preview.id)
                share_url = share.get("share_url") if isinstance(share, dict) else getattr(share, "share_url", None)
                print(f"     share_url={share_url}")
            except (AttributeError, MiosaError, KeyError) as err:
                print(f"     (share endpoint not exposed via this sandbox helper: {err})")

            # 6. Publish (Phase 2B/3 — currently routes through sandbox-backed bridge)
            print("[6] publishing …", flush=True)
            try:
                result = miosa.deployments.publish_from_sandbox(
                    sandbox.id,
                    kind="static",
                    environment="production",
                    output_path="/workspace",
                    external_workspace_id=ext_workspace,
                    external_user_id=ext_user,
                    external_project_id=ext_project,
                )
                print(f"     deployment result: {result}")
            except MiosaError as err:
                print(f"     publish not yet wired in this backend: {err}")
        finally:
            # Cleanup
            print("[cleanup] destroying sandbox", flush=True)
            try:
                sandbox.destroy()
            except Exception:
                pass


if __name__ == "__main__":
    main()
