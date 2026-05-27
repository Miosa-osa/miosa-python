from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx

from .types import ProviderMessage, ProviderStepResult, Tool, ToolCall


@dataclass
class OpenAICompatibleProvider:
    name: str
    model: str
    base_url: str
    api_key: str | None = None
    max_tokens: int = 4096
    temperature: float | None = None
    headers: dict[str, str] = field(default_factory=dict)

    def step(
        self,
        *,
        messages: Sequence[ProviderMessage],
        tools: Sequence[Tool],
        system: str | None = None,
    ) -> ProviderStepResult:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": _to_chat_messages(messages, system),
            "max_tokens": self.max_tokens,
        }
        if tools:
            body["tools"] = [_to_chat_tool(tool) for tool in tools]
            body["tool_choice"] = "auto"
        if self.temperature is not None:
            body["temperature"] = self.temperature

        headers = {"content-type": "application/json", **self.headers}
        if self.api_key:
            headers["authorization"] = f"Bearer {self.api_key}"

        with httpx.Client(timeout=90) as client:
            response = client.post(self.base_url, headers=headers, json=body)
        if response.status_code >= 400:
            raise RuntimeError(_provider_error(self.name, response))

        payload = response.json()
        choice = (payload.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        raw_tool_calls = message.get("tool_calls") or []
        tool_calls = [
            ToolCall(
                id=call.get("id") or f"call_{index}",
                name=((call.get("function") or {}).get("name") or ""),
                input=_parse_args((call.get("function") or {}).get("arguments") or "{}"),
            )
            for index, call in enumerate(raw_tool_calls)
            if ((call.get("function") or {}).get("name") or "")
        ]
        usage = payload.get("usage") or {}

        return ProviderStepResult(
            text=_content_to_text(message.get("content")),
            tool_calls=tool_calls,
            stop_reason=_finish_reason(choice.get("finish_reason"), len(tool_calls)),
            usage={
                "input_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
                "output_tokens": int(
                    usage.get("completion_tokens") or usage.get("output_tokens") or 0
                ),
            }
            if usage
            else None,
        )


def openai_compatible_provider(
    *,
    model: str,
    base_url: str = "https://api.openai.com/v1/chat/completions",
    api_key: str | None = None,
    name: str = "openai-compatible",
    max_tokens: int = 4096,
    temperature: float | None = None,
    headers: dict[str, str] | None = None,
) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        name=name,
        model=model,
        base_url=base_url,
        api_key=api_key,
        max_tokens=max_tokens,
        temperature=temperature,
        headers=headers or {},
    )


def openai_provider(**kwargs: Any) -> OpenAICompatibleProvider:
    return openai_compatible_provider(
        name="openai",
        base_url=kwargs.pop("base_url", "https://api.openai.com/v1/chat/completions"),
        **kwargs,
    )


def groq_provider(**kwargs: Any) -> OpenAICompatibleProvider:
    return openai_compatible_provider(
        name="groq",
        base_url=kwargs.pop("base_url", "https://api.groq.com/openai/v1/chat/completions"),
        **kwargs,
    )


def deepseek_provider(**kwargs: Any) -> OpenAICompatibleProvider:
    return openai_compatible_provider(
        name="deepseek",
        base_url=kwargs.pop("base_url", "https://api.deepseek.com/chat/completions"),
        **kwargs,
    )


def openrouter_provider(**kwargs: Any) -> OpenAICompatibleProvider:
    return openai_compatible_provider(
        name="openrouter",
        base_url=kwargs.pop("base_url", "https://openrouter.ai/api/v1/chat/completions"),
        **kwargs,
    )


def together_provider(**kwargs: Any) -> OpenAICompatibleProvider:
    return openai_compatible_provider(
        name="together",
        base_url=kwargs.pop("base_url", "https://api.together.xyz/v1/chat/completions"),
        **kwargs,
    )


def fireworks_provider(**kwargs: Any) -> OpenAICompatibleProvider:
    return openai_compatible_provider(
        name="fireworks",
        base_url=kwargs.pop(
            "base_url", "https://api.fireworks.ai/inference/v1/chat/completions"
        ),
        **kwargs,
    )


def mistral_provider(**kwargs: Any) -> OpenAICompatibleProvider:
    return openai_compatible_provider(
        name="mistral",
        base_url=kwargs.pop("base_url", "https://api.mistral.ai/v1/chat/completions"),
        **kwargs,
    )


def cerebras_provider(**kwargs: Any) -> OpenAICompatibleProvider:
    return openai_compatible_provider(
        name="cerebras",
        base_url=kwargs.pop("base_url", "https://api.cerebras.ai/v1/chat/completions"),
        **kwargs,
    )


def perplexity_provider(**kwargs: Any) -> OpenAICompatibleProvider:
    return openai_compatible_provider(
        name="perplexity",
        base_url=kwargs.pop("base_url", "https://api.perplexity.ai/chat/completions"),
        **kwargs,
    )


def xai_provider(**kwargs: Any) -> OpenAICompatibleProvider:
    return openai_compatible_provider(
        name="xai",
        base_url=kwargs.pop("base_url", "https://api.x.ai/v1/chat/completions"),
        **kwargs,
    )


def ollama_provider(**kwargs: Any) -> OpenAICompatibleProvider:
    return openai_compatible_provider(
        name="ollama",
        base_url=kwargs.pop("base_url", "http://localhost:11434/v1/chat/completions"),
        **kwargs,
    )


def lm_studio_provider(**kwargs: Any) -> OpenAICompatibleProvider:
    return openai_compatible_provider(
        name="lmstudio",
        base_url=kwargs.pop("base_url", "http://localhost:1234/v1/chat/completions"),
        **kwargs,
    )


def _to_chat_messages(
    messages: Sequence[ProviderMessage],
    system: str | None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if system:
        out.append({"role": "system", "content": system})
    for message in messages:
        if message.role == "tool":
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": message.tool_use_id or "",
                    "content": message.tool_output or "",
                }
            )
        elif message.role == "assistant":
            item: dict[str, Any] = {
                "role": "assistant",
                "content": message.content or None,
            }
            if message.tool_calls:
                item["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.input),
                        },
                    }
                    for call in message.tool_calls
                ]
            out.append(item)
        else:
            out.append({"role": "user", "content": message.content})
    return out


def _to_chat_tool(tool: Tool) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema,
        },
    }


def _parse_args(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}
    return value if isinstance(value, dict) else {}


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    return ""


def _finish_reason(
    reason: str | None,
    tool_count: int,
) -> Literal["end_turn", "tool_use", "max_tokens", "stop_sequence", "other"]:
    if tool_count:
        return "tool_use"
    if reason == "stop":
        return "end_turn"
    if reason in {"tool_calls", "function_call"}:
        return "tool_use"
    if reason == "length":
        return "max_tokens"
    return "other"


def _provider_error(name: str, response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict) and error.get("message"):
        return f"{name}: HTTP {response.status_code}: {error['message']}"
    return f"{name}: HTTP {response.status_code}: {response.text[:500]}"
