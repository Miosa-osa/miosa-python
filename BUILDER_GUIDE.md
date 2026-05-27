# Build Your Own Lovable With MIOSA Sandboxes

The Python agent SDK lets your product run a prompt-to-app builder on top of
MIOSA sandboxes.

Use it for:

- AI website builders with live previews
- AI app builders with source files, shell commands, tests, and dev servers
- artifact builders that generate docs, reports, and export bundles
- slide deck builders that render and repair decks in a sandbox

## Minimal Website Builder

```python
import os
from miosa.agent import Agent, groq_provider, sandbox_builder_system_prompt

agent = Agent(
    provider=groq_provider(
        api_key=os.environ["GROQ_API_KEY"],
        model="moonshotai/kimi-k2-instruct-0905",
    ),
    miosa_api_key=os.environ["MIOSA_API_KEY"],
    miosa_tool_options={"allow_destroy": False},
)

result = agent.run(
    "Build a landing page for a boutique gym. Run it on port 3000 and give me the preview URL.",
    system=sandbox_builder_system_prompt("website"),
    max_iterations=12,
)

print(result.final_text)
```

## Product Pattern

1. Create one sandbox per project or generation run.
2. Give the agent the builder preset and a user prompt.
3. Stream steps into your UI as command logs and file activity.
4. Show the preview URL in an iframe.
5. Let the user ask for revisions against the same sandbox.
6. Export, publish, snapshot, or destroy the sandbox when done.

## Presets

```python
sandbox_builder_system_prompt("website")
sandbox_builder_system_prompt("app")
sandbox_builder_system_prompt("artifact")
sandbox_builder_system_prompt("slide_deck")
```

These prompts make the agent work under `/workspace`, run and verify outputs,
return file paths and preview URLs, and keep the sandbox alive unless cleanup is
requested.

Runnable examples:

- `examples/agent_sandbox_website_builder.py`
- `examples/agent_sandbox_app_builder.py`
- `examples/agent_sandbox_artifact_builder.py`
- `examples/agent_sandbox_slide_deck_builder.py`
