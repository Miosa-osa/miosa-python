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

# Boot a computer, run a command, expose a preview
computer = miosa.computers.create(
    name="my-build",
    template_type="miosa-sandbox",
    size="small",
)
computer.start()
computer.wait(status="running")

result = computer.exec.run("python --version")
print(result.stdout)   # Python 3.12.x

computer.files.write_file("/workspace/hello.py", "print('hello from miosa')")
out = computer.exec.run("python /workspace/hello.py")
print(out.stdout)      # hello from miosa

print(computer.preview_url(8000, "/"))
# https://8000-<slug>.sandbox.miosa.ai/

computer.destroy()
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
    "Create a sandbox, write /workspace/hello.py, run it, show me the output, "
    "then destroy the sandbox.",
    max_iterations=10,
)

print(result.final_text)
```

Built-in agent tools expose the computer primitive in plain terms:

| Tool | Does |
|---|---|
| `create_sandbox` | Boot a fast code sandbox computer for shell/Python/Node/files. |
| `create_computer` | Boot a general MIOSA computer for GUI, services, previews, files. |
| `list_computers` | List active computers, sandboxes, and desktops. |
| `get_computer` | Fetch status, template, size, and public URL. |
| `exec` / `exec_python` | Run bash or Python inside the computer. |
| `read_file` / `write_file` / `list_files` | Work with files inside the computer. |
| `preview_url` | Get the public HTTPS URL for a service port. |
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

## License

MIT
