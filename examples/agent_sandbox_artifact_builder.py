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
    "Create a launch-plan artifact pack for a new AI website builder: README.md, "
    "pricing.md, launch-checklist.md, and a sample customer-onboarding email. "
    "List the generated files and summarize the contents.",
    system=(
        "You are an artifact builder. Use the sandbox filesystem as the artifact "
        "workspace. Create durable files under /workspace/artifacts and verify "
        "them before replying."
    ),
    max_iterations=14,
)

print(result.final_text)
