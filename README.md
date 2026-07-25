# miosa (Python)

> Official Python SDK for MIOSA — the AI cloud platform for sandboxes, computers, deployments, and managed data.

[![PyPI version](https://img.shields.io/pypi/v/miosa.svg)](https://pypi.org/project/miosa/)
[![Python versions](https://img.shields.io/pypi/pyversions/miosa.svg)](https://pypi.org/project/miosa/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docs](https://img.shields.io/badge/docs-miosa.ai%2Fdocs-blue)](https://miosa.ai/docs/sdks/python)

## Install

```bash
pip install miosa
# or
uv add miosa
# or
poetry add miosa
```

Requires Python 3.9+. Dependencies: `httpx`, `pydantic v2`.

## Quickstart

```python
from miosa import Miosa

miosa = Miosa(api_key="msk_live_...")

# Create or resume a persistent sandbox workspace, then work inside it.
sb = miosa.sandboxes.create_agent_workspace(
    "my-build",
    external_workspace_id="customer-workspace-123",
)

result = sb.exec.run("python --version")
print(result.stdout)   # Python 3.12.x

sb.files.write("/workspace/hello.py", "print('hello from miosa')")
out = sb.exec.run("python /workspace/hello.py")
print(out.stdout)      # hello from miosa

print(sb.preview.create(port=8000)["url"])
# https://8000-<slug>.sandbox.miosa.ai/

sb.snapshots.create("after-hello-world")
sb.pause()
```

## What's included

| Resource | Description |
|---|---|
| `miosa.computers` | Firecracker microVMs — full lifecycle, exec, files, services |
| `miosa.sandboxes` | Lightweight code-execution VMs via the `/sandboxes` route |
| `miosa.deployments` | Versioned production releases with rollback |
| `miosa.databases` | Managed Postgres / Redis lifecycle |
| `miosa.storage` | S3-compatible object storage |
| `miosa.volumes` | Persistent block storage |
| `miosa.api_keys` | Programmatic API key management |
| `miosa.usage` | Usage reports per workspace, per external tenant |
| `miosa.settings` | Workspace config, branding, BYOK provider keys |
| `miosa.webhooks` | Outgoing tenant webhooks — CRUD, test, delivery history |
| `miosa.open_computers` | BYOC host management — register your own machines |
| `miosa.devices` | Unified device facade for sandbox/computer list, exec, files, previews |
| `miosa.connectors` | Provider credentials and short-lived runtime tokens |
| `miosa.runtime_env` | Inherited tenant/workspace/project runtime environment variables |

## Computers and Desktop Access

`computer` is the user-facing product. `miosa-desktop` is the desktop computer
template/profile. The canonical fast desktop profile is:

```python
computer = miosa.computers.create(
    name="agent-desktop",
    template_type="miosa-desktop",
    size="small",  # 2 vCPU / 4 GB
)
```

Authenticated platform desktop links do not need a viewer password. Raw
external viewer links such as `*.computer.miosa.ai/desktop/index.html` are
password-gated; rotate the password when you need to share that raw link:

```python
status = computer.viewer_password()
rotated = computer.rotate_viewer_password()
print(rotated["viewer_password"])
```

## Connect vs Egress

Use **Connect** when your product needs to manage provider credentials for
agents, sandboxes, computers, or deployments. Connect owns the product-level
contract: connectors, installations, project links, inherited defaults,
short-lived tokens, white-label attribution, and runtime bindings.

Use **Egress** when you need the low-level security boundary: encrypted secret
storage, outbound host allowlists, placeholder token exchange, and audit logs.
Egress is the enforcement layer under Connect. Most white-label apps should
call `miosa.connectors` and runtime binding helpers first; only call
`miosa.secrets`, `miosa.network`, or `miosa.audit` when you are building
security/admin controls directly.

```python
import os

connector = miosa.connectors.create(
    "anthropic",
    name="workspace-claude",
    scope="workspace",
    external_workspace_id="clinic-iq",
    value=os.environ["ANTHROPIC_API_KEY"],
)

# Runtime-level materialization: the sandbox sees ANTHROPIC_API_KEY, but your
# app does not get the raw provider key back from MIOSA.
miosa.connectors.materialize_defaults(
    workspace_id="workspace-id",
    resource_type="sandbox",
    resource_id=sb.id,
    target="agent",
    external_workspace_id="clinic-iq",
)
```

## Agent workspaces

For AI builders, code assistants, and white-label agent products, the sandbox
is the development machine. Do not run builds on the user's laptop and upload
the result as the primary flow. Create or resume a stable sandbox workspace,
write files under `/workspace`, run package installs/tests/builds inside the
sandbox, expose previews from the sandbox, and publish from that sandbox.

```python
sb = miosa.sandboxes.get_or_create(
    "acme-marketing-page",
    template_id="miosa-sandbox",
    persistent=True,
    timeout_sec=86_400,
    idle_timeout_sec=1800,
    snapshot_expiration_days=30,
    keep_last_snapshots=1,
    external_workspace_id="acme",
    external_user_id="jane",
    wait_until_ready=True,
)

sb.files.write_files([
    {"path": "/workspace/package.json", "data": '{"scripts":{"dev":"vite --host 0.0.0.0"}}'},
    {"path": "/workspace/index.html", "data": '<main id="app"></main>'},
])

for event in sb.exec_stream("cd /workspace && npm install && npm run dev -- --port 3000"):
    print(event)

preview = sb.preview.create(port=3000)
print(preview["url"])
```

For platform agents that plan work outside the sandbox and then hand execution
to a runtime inside the sandbox/computer, use the unified device API:

```python
miosa.agent_runtime_profiles.create(
    workspace_id="clinic-workspace",
    name="ClinicIQ Claude Code",
    runtime="claude-code",
    is_default=True,
    connectors=[
        "anthropic/cliniciq",
        {
            "uid": "refero",
            "type": "mcp",
            "managed": True,
            "server_url": "https://api.refero.design/mcp",
        },
    ],
    env={"ANTHROPIC_API_KEY": "miosa-managed:anthropic/cliniciq"},
    metadata={"model": "claude-opus-4.8", "white_label_client": "cliniciq"},
)

miosa.devices.write_file(
    sb.id,
    "/workspace/PLAN.md",
    content="# Build plan\nUse the customer profile and export /workspace/out.",
)

build = miosa.devices.exec(
    sb.id,
    "npm install && npm run build",
    cwd="/workspace",
    timeout_ms=600_000,
)

artifact = miosa.devices.read_file(sb.id, "/workspace/out/report.pdf")
```

`create_agent_workspace()` is a convenience wrapper around `get_or_create()`
with builder defaults: a 24-hour activity cap, thirty-minute idle
snapshot/pause, readiness waiting, 30-day snapshot-retention metadata,
keep-last-snapshot metadata, and metadata that marks the sandbox as an agent
workspace.

That mirrors the Vercel-style persistent-sandbox model without keeping CPU
running forever: activity extends the running session, idle workspaces are
checkpointed and paused, and later sessions resume from the checkpoint. Use
`extend(86_400)` before long builds, `pause()` when the user is done for now,
`resume()` for the next session, `snapshots.create()` for manual checkpoints,
and `destroy()` only when the workspace should be permanently deleted.

## Agent SDK

The Python SDK includes a small agent loop plus provider adapters and a MIOSA
tool catalogue. This is the quickest path when you want an LLM to operate
MIOSA computers directly.

```python
from miosa.agent import Agent, groq_provider

agent = Agent(
    provider=groq_provider(
        api_key="gsk_...",
        model="moonshotai/kimi-k2-instruct-0905",
    ),
    miosa_api_key="msk_live_...",
)

result = agent.run(
    "Create a sandbox workspace, write /workspace/hello.py, run it, show me "
    "the output, snapshot it, then pause the sandbox.",
    max_iterations=10,
)

print(result.final_text)
```

Built-in agent tools expose the computer primitive in plain terms:

| Tool | Does |
|---|---|
| `create_sandbox` | Create/resume a persistent code sandbox workspace for shell/Python/Node/files. |
| `create_computer` | Boot a general MIOSA computer for GUI, services, previews, files. |
| `list_computers` | List active computers, sandboxes, and desktops. |
| `get_computer` | Fetch status, template, size, and public URL. |
| `exec` / `exec_python` | Run bash or Python inside the computer. |
| `read_file` / `write_file` / `list_files` | Work with files inside the computer. |
| `preview_url` | Get the public HTTPS URL for a service port. |
| `pause_sandbox` / `resume_sandbox` | Stop/resume a persistent workspace without deleting files. |
| `extend_sandbox` | Extend the activity timeout before long installs, builds, or agent tasks. |
| `snapshot_sandbox` | Create a checkpoint after dependency install or a good edit. |
| `deploy_sandbox` | Publish to normal MIOSA Deploy. |
| `deploy_docker` | Publish to the workspace App Engine appliance. |
| `destroy_computer` | Release compute resources when done. |

Provider factories include `openai_provider`, `groq_provider`,
`deepseek_provider`, `openrouter_provider`, `together_provider`,
`fireworks_provider`, `mistral_provider`, `cerebras_provider`,
`perplexity_provider`, `xai_provider`, `ollama_provider`, `lm_studio_provider`,
and `openai_compatible_provider` for custom routers.

Sandbox-first builder examples live in `examples/`:

See [BUILDER_GUIDE.md](./BUILDER_GUIDE.md) for the full “build your own
Lovable with MIOSA sandboxes” product pattern.

| Example | What it builds |
|---|---|
| `agent_sandbox_website_builder.py` | A Lovable-style website builder flow. |
| `agent_sandbox_app_builder.py` | A small app builder with a dev server and preview. |
| `agent_sandbox_artifact_builder.py` | Markdown/doc artifacts in `/workspace/artifacts`. |
| `agent_sandbox_slide_deck_builder.py` | A deck workspace under `/workspace/deck`. |

Set `GROQ_API_KEY` and `MIOSA_API_KEY`, then run one of the examples. They keep
the sandbox alive with `miosa_tool_options={"allow_destroy": False}` so your app
can show previews, inspect generated files, or publish later.

The agent should treat a MIOSA sandbox like the actual development machine:
write source files under `/workspace`, run package managers/tests/builds inside
the sandbox, start dev servers inside the sandbox, stream logs/tool results back
to your UI, and only publish after a sandbox preview passes a smoke check.

## File operations

```python
# Write / read
computer.files.write_file("/workspace/config.json", '{"key": "value"}')
text = computer.files.read_file("/workspace/config.json")

# Upload / download
computer.files.upload("/local/report.pdf", "/workspace/report.pdf")
raw_bytes = computer.files.download("/workspace/report.pdf")

# List / stat / mkdir / rename / chmod
entries = computer.files.list("/workspace")
stat    = computer.files.stat("/workspace/config.json")
computer.files.mkdir("/workspace/output", recursive=True)
computer.files.rename("/workspace/old.txt", "/workspace/new.txt")
computer.files.chmod("/workspace/run.sh", 0o755)
```

## Services (background processes)

```python
svc = computer.services.create(
    name="api",
    command="uvicorn app:main --port 8080",
    working_dir="/workspace",
    env={"DEBUG": "1"},
    port=8080,
)

for log in computer.services.logs(svc.id, follow=True):
    print(log.stream, log.line)

computer.services.restart(svc.id)
computer.services.delete(svc.id)
```

## Publish from sandbox

Sandbox previews are mutable builder URLs. Publishing creates a durable
deployment version with a stable `url` / `public_url`.

```python
sb = miosa.sandboxes.create(name="clinic-intake", template_id="miosa-sandbox")
sb.files.write_file("/workspace/index.html", "<h1>Clinic intake</h1>")

result = sb.deploy(
    name="clinic-intake",
    output_path="/workspace",
    entrypoint="index.html",
)
print(result["url"])
```

For full-stack/dynamic apps:

```python
result = sb.deploy(
    name="clinic-intake-api",
    output_path="/workspace",
    build_command="npm run build",
    run_command="npm start",
    port=3000,
    health_check_path="/",
    resources={
        "database": {"auto": True, "engine": "postgresql", "size": "xs"},
        "storage": {"auto": True},
    },
    domain="intake.apps.cliniciq.com",
)
```

If `result["state"] == "building"` for a dynamic app, poll
`miosa.deployments.get(result["deployment_id"])` until it is `running`. Always
display the server-returned `url` / `public_url`; do not hardcode
`preview.miosa.app`, `api.miosa.app`, or `<tenant>.miosa.app`.

For workspace App Engine, publish from the same sandbox but choose the
App Engine target:

```python
result = sb.deploy_docker(
    name="lead-magnet",
    path="/workspace",
    build_command="npm run build",
    run_command="npm start",
    port=3000,
)
print(result.get("url") or result.get("public_url"))
```

App Engine runs app containers inside the workspace's dedicated MIOSA
App Engine appliance VM. It is separate from normal MIOSA dynamic runtime
VMs and is useful when a workspace needs many small apps, funnels, lead
magnets, APIs, or client sites.

## Desktop control

```python
screenshot = computer.screenshot()          # PNG bytes
computer.click(640, 400)
computer.double_click(640, 400)
computer.type("hello world")
computer.key("Return")
computer.scroll("down", 3)
computer.drag(100, 100, 400, 400)

cursor = computer.cursor()
windows = computer.windows()
computer.launch("firefox")
```

## Async usage

```python
import asyncio
from miosa import AsyncMiosa

async def main():
    async with AsyncMiosa(api_key="msk_live_...") as miosa:
        computer = await miosa.computers.create(
            name="async-build", template_type="miosa-sandbox"
        )
        await computer.files.write_file("/workspace/app.py", "print('async!')")
        result = await computer.exec.run("python /workspace/app.py")
        print(result.stdout)
        await computer.destroy()

asyncio.run(main())
```

## White-label / multi-tenant

Tag resources with `external_workspace_id` and `external_user_id` to attribute usage to your downstream customers:

```python
computer = miosa.computers.create(
    name="customer-build",
    template_type="miosa-sandbox",
    metadata={
        "external_workspace_id": "dental-office-123",
        "external_user_id": "dr-smith-456",
    },
)
```

White-label URL layers are separate:

```text
sandbox preview:     https://<port>-<slug>.sandbox.<preview-domain>
durable deployment:  https://<slug>.<deployment-domain>
custom domain:       https://app.customer.com
```

Tenant preview-domain management is available through `miosa.tenant`. Tenant
deployment-domain routing exists server-side; clients should consume deployment
`public_url` instead of reconstructing it.

## Runs

Use an idempotency key when a caller may retry run creation.
The same key prevents a retry from creating duplicate work.

```python
run = miosa.runs.run(
    sandbox_id="sbx_abc123",
    instruction="Build the ClinicIQ report",
    idempotency_key="clinic-iq-request-123",
)

events = miosa.runs.events(run["id"], limit=200)
for event in events:
    print(event["type"], event.get("metadata", {}))

# Continue from the last durable event without replaying earlier events.
new_events = miosa.runs.events(run["id"], after_id=events[-1]["id"])
```

The async client exposes the same contract through `await client.runs.run(...)` and `await client.runs.events(...)`.

## Error handling

```python
from miosa import (
    AuthenticationError, NotFoundError, RateLimitError, MiosaError
)

try:
    computer = miosa.computers.get("cmp_doesnt_exist")
except NotFoundError:
    print("Computer not found")
except RateLimitError as e:
    print(f"Rate limited; retry after {e.retry_after}s")
except AuthenticationError:
    print("Check your API key")
except MiosaError as e:
    print(f"API error {e.status}: {e.message}")
```

Exception hierarchy: `MiosaError` > `AuthenticationError` (401), `InsufficientCreditsError` (402), `PermissionError` (403), `NotFoundError` (404), `ValidationError` (422), `RateLimitError` (429), `ServerError` (5xx), `ConnectionError`, `TimeoutError`.

## Configuration

| Option | Env var | Default |
|---|---|---|
| `api_key` | `MIOSA_API_KEY` | — |
| `base_url` | `MIOSA_BASE_URL` | `https://api.miosa.ai/api/v1` |
| `timeout` | — | 30s |
| `max_retries` | — | 3 |

## Links

- [Full documentation](https://miosa.ai/docs/sdks/python)
- [Quickstart](https://miosa.ai/docs/quickstart)
- [GitHub](https://github.com/Miosa-osa/miosa-python)
- [Contact](mailto:platform@miosa.ai)

## Phase 1-4 methods (v1.1.0)

**Preview tokens and share URLs**

```python
# Mint a scoped preview token (e.g. for iframe embed)
token = sb.preview_token(expires_in=3600, scope="read")
print(token["url"])  # https://...?mt=mp_<token>

# Create a public share link (no API key required)
share = sb.share.create(expires_in=7200)
print(share["share_url"])
```

**File tree and batch write**

```python
tree = sb.files.tree("/workspace", depth=2)
sb.files.write_many([
    {"path": "/workspace/app.py", "content": "print('hello')"},
    {"path": "/workspace/cfg.json", "content": b"{}"},
])
```

**Tenant events stream and quotas**

```python
for event in client.events.stream(types=["sandbox.*"]):
    print(event["_event_type"], event)

client.quotas.set("usr_abc", max_sandboxes=10, max_concurrent=3)
```

**Webhook signature verification**

```python
from miosa.resources.webhooks import Webhooks

ok = Webhooks.verify_signature(request.body, request.headers["X-Miosa-Signature"], secret)
```

## License

MIT
