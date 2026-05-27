from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from ..client import Miosa
from .tools import miosa_tools
from .types import (
    AgentResult,
    AgentStep,
    ExecutedToolCall,
    Provider,
    ProviderMessage,
    Tool,
)


class Agent:
    """Runs an LLM/tool loop with MIOSA computers available as tools."""

    def __init__(
        self,
        *,
        provider: Provider,
        tools: Sequence[Tool] | None = None,
        miosa_api_key: str | None = None,
        miosa_base_url: str | None = None,
        miosa_tool_options: dict[str, Any] | None = None,
    ) -> None:
        self.provider = provider
        self._miosa: Miosa | None = None
        if tools is not None:
            self.tools = list(tools)
        elif miosa_api_key is not None:
            self._miosa = Miosa(api_key=miosa_api_key, base_url=miosa_base_url)
            self.tools = miosa_tools(self._miosa, **(miosa_tool_options or {}))
        else:
            raise ValueError("Agent requires either tools= or miosa_api_key=")

        self._tools_by_name: dict[str, Tool] = {}
        for tool in self.tools:
            if tool.name in self._tools_by_name:
                raise ValueError(f"duplicate tool name: {tool.name}")
            self._tools_by_name[tool.name] = tool

    def run(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_iterations: int = 10,
        on_step: Callable[[AgentStep], None] | None = None,
    ) -> AgentResult:
        messages = [ProviderMessage(role="user", content=prompt)]
        steps: list[AgentStep] = []
        final_text = ""

        for index in range(max_iterations):
            try:
                step_result = self.provider.step(
                    system=system,
                    messages=messages,
                    tools=self.tools,
                )
            except Exception as exc:
                return AgentResult(
                    final_text=final_text,
                    steps=steps,
                    stop_reason="error",
                    error=f"provider step {index} failed: {exc}",
                )

            messages.append(
                ProviderMessage(
                    role="assistant",
                    content=step_result.text,
                    tool_calls=step_result.tool_calls,
                )
            )

            executed: list[ExecutedToolCall] = []
            for call in step_result.tool_calls:
                tool = self._tools_by_name.get(call.name)
                is_error = False
                if tool is None:
                    output = (
                        f"Error: unknown tool '{call.name}'. Available: "
                        + ", ".join(self._tools_by_name)
                    )
                    is_error = True
                else:
                    try:
                        output = tool.execute(call.input)
                        is_error = output.startswith("Error:")
                    except Exception as exc:
                        output = f"Error executing {call.name}: {exc}"
                        is_error = True

                executed.append(
                    ExecutedToolCall(
                        id=call.id,
                        name=call.name,
                        input=call.input,
                        output=output,
                        is_error=is_error,
                    )
                )
                messages.append(
                    ProviderMessage(
                        role="tool",
                        tool_use_id=call.id,
                        tool_name=call.name,
                        tool_output=output,
                        tool_is_error=is_error,
                    )
                )

            step = AgentStep(
                index=index,
                text=step_result.text,
                tool_calls=executed,
                usage=step_result.usage,
            )
            steps.append(step)
            final_text += step_result.text
            if on_step is not None:
                on_step(step)

            if step_result.stop_reason == "stop_sequence":
                return AgentResult(final_text, steps, "stop_sequence")
            if step_result.stop_reason == "end_turn" and not step_result.tool_calls:
                return AgentResult(final_text, steps, "end_turn")
            if not step_result.tool_calls and step_result.stop_reason != "tool_use":
                return AgentResult(final_text, steps, "end_turn")

        return AgentResult(final_text, steps, "max_iterations")
