import os

from miosa.agent import Agent, groq_provider

agent = Agent(
    provider=groq_provider(
        api_key=os.environ["GROQ_API_KEY"],
        model=os.environ.get("GROQ_MODEL", "moonshotai/kimi-k2-instruct-0905"),
    ),
    miosa_api_key=os.environ["MIOSA_API_KEY"],
    miosa_tool_options={"default_size": "medium", "allow_destroy": False},
)

result = agent.run(
    "Build a tiny CRM app with a contact list, search box, add-contact form, "
    "and clean UI. Use whatever stack is fastest in the sandbox.",
    system=(
        "You are an app builder running inside MIOSA sandboxes. Write source "
        "files, install only necessary packages, start a dev server, smoke test "
        "it, and return the preview URL. Do not destroy the sandbox."
    ),
    max_iterations=18,
)

print(result.final_text)
