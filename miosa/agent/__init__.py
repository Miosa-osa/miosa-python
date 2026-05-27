"""Agent Development Kit for MIOSA.

Example::

    from miosa.agent import Agent, groq_provider

    agent = Agent(
        provider=groq_provider(api_key="gsk_...", model="moonshotai/kimi-k2-instruct-0905"),
        miosa_api_key="msk_u_...",
    )
    result = agent.run("Create a sandbox, write hello.py, run it, then clean up.")
"""

from .core import Agent
from .presets import sandbox_builder_system_prompt, sandbox_builder_system_prompts
from .providers import (
    cerebras_provider,
    deepseek_provider,
    fireworks_provider,
    groq_provider,
    lm_studio_provider,
    mistral_provider,
    ollama_provider,
    openai_compatible_provider,
    openai_provider,
    openrouter_provider,
    perplexity_provider,
    together_provider,
    xai_provider,
)
from .tools import miosa_tools
from .types import AgentResult, AgentStep, Provider, ProviderMessage, ProviderStepResult, Tool

__all__ = [
    "Agent",
    "AgentResult",
    "AgentStep",
    "Provider",
    "ProviderMessage",
    "ProviderStepResult",
    "Tool",
    "miosa_tools",
    "sandbox_builder_system_prompt",
    "sandbox_builder_system_prompts",
    "openai_compatible_provider",
    "openai_provider",
    "groq_provider",
    "deepseek_provider",
    "openrouter_provider",
    "together_provider",
    "fireworks_provider",
    "mistral_provider",
    "cerebras_provider",
    "perplexity_provider",
    "xai_provider",
    "ollama_provider",
    "lm_studio_provider",
]
