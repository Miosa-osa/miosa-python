from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

ToolInput = dict[str, Any]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    execute: Callable[[ToolInput], str]


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    input: ToolInput


@dataclass
class ProviderMessage:
    role: Literal["user", "assistant", "tool"]
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_use_id: str | None = None
    tool_name: str | None = None
    tool_output: str | None = None
    tool_is_error: bool = False


@dataclass(frozen=True)
class ProviderStepResult:
    text: str
    tool_calls: list[ToolCall]
    stop_reason: Literal["end_turn", "tool_use", "max_tokens", "stop_sequence", "other"]
    usage: dict[str, int] | None = None


class Provider(Protocol):
    name: str
    model: str

    def step(
        self,
        *,
        messages: Sequence[ProviderMessage],
        tools: Sequence[Tool],
        system: str | None = None,
    ) -> ProviderStepResult: ...


@dataclass(frozen=True)
class ExecutedToolCall:
    id: str
    name: str
    input: ToolInput
    output: str
    is_error: bool


@dataclass(frozen=True)
class AgentStep:
    index: int
    text: str
    tool_calls: list[ExecutedToolCall]
    usage: dict[str, int] | None = None


@dataclass(frozen=True)
class AgentResult:
    final_text: str
    steps: list[AgentStep]
    stop_reason: Literal["end_turn", "max_iterations", "stop_sequence", "error"]
    error: str | None = None
