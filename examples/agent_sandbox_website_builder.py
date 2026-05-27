import os

from miosa.agent import Agent, groq_provider

agent = Agent(
    provider=groq_provider(
        api_key=os.environ["GROQ_API_KEY"],
        model=os.environ.get("GROQ_MODEL", "moonshotai/kimi-k2-instruct-0905"),
    ),
    miosa_api_key=os.environ["MIOSA_API_KEY"],
    miosa_tool_options={"allow_destroy": False},
)

result = agent.run(
    "Build a polished one-page website for a local dental clinic. Use a single "
    "index.html with CSS and JS, run it on port 3000, and give me the preview URL.",
    system=(
        "You are a sandbox-first website builder. Create files in /workspace, "
        "run the app, and return the preview URL. Do not destroy the sandbox."
    ),
    max_iterations=12,
)

print(result.final_text)
