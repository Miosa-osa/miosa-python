import os

from miosa.agent import Agent, groq_provider

agent = Agent(
    provider=groq_provider(
        api_key=os.environ["GROQ_API_KEY"],
        model=os.environ.get("GROQ_MODEL", "moonshotai/kimi-k2-instruct-0905"),
    ),
    miosa_api_key=os.environ["MIOSA_API_KEY"],
    miosa_tool_options={"default_size": "small", "allow_destroy": False},
)

result = agent.run(
    "Build a 7-slide investor deck for a sandbox-native AI app builder. Make it "
    "concise, visual, and ready to export. Return the file paths and preview instructions.",
    system=(
        "You are a slide deck builder. Generate the deck source in the sandbox, "
        "render or export it when possible, and keep outputs under /workspace/deck. "
        "Do not destroy the sandbox."
    ),
    max_iterations=16,
)

print(result.final_text)
