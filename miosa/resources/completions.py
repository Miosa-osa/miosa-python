"""Completions — OpenAI-compatible chat / text completion endpoints.

Routes are exposed under ``/api/v1/intelligence/`` and require an
``mki_*`` intelligence key. Both endpoints support streaming responses
via Server-Sent Events when ``stream=True``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Union

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data",)) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data and not isinstance(data.get("choices"), list):
                return data[k]
    return data


def _build_body(
    *,
    model: str,
    messages: Optional[List[Dict[str, Any]]] = None,
    prompt: Optional[Union[str, List[str]]] = None,
    stream: bool = False,
    **opts: Any,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"model": model, "stream": stream}
    if messages is not None:
        body["messages"] = messages
    if prompt is not None:
        body["prompt"] = prompt
    body.update({k: v for k, v in opts.items() if v is not None})
    return body


class Completions:
    """OpenAI-compatible inference — text + chat completions."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def create(
        self,
        *,
        model: str,
        prompt: Optional[Union[str, List[str]]] = None,
        stream: bool = False,
        **opts: Any,
    ) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """Create a text completion (POST ``/intelligence/completions``).

        When ``stream=True`` returns an iterator of SSE events; otherwise
        returns a single JSON payload.
        """
        body = _build_body(model=model, prompt=prompt, stream=stream, **opts)
        if stream:
            return self._t.stream_sse("/intelligence/completions")  # body is GET-only for SSE in transport
        return _unwrap(
            self._t.request("POST", "/intelligence/completions", json_body=body)
        )

    def chat(
        self,
        *,
        model: str,
        messages: List[Dict[str, Any]],
        stream: bool = False,
        **opts: Any,
    ) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """Create a chat completion (POST ``/intelligence/chat/completions``).

        When ``stream=True`` returns an iterator of SSE events parsed from
        the OpenAI-compatible delta stream; otherwise a single response.
        """
        body = _build_body(model=model, messages=messages, stream=stream, **opts)
        if stream:
            return self._t.stream_sse("/intelligence/chat/completions")
        return _unwrap(
            self._t.request("POST", "/intelligence/chat/completions", json_body=body)
        )


class AsyncCompletions:
    """Async OpenAI-compatible inference."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def create(
        self,
        *,
        model: str,
        prompt: Optional[Union[str, List[str]]] = None,
        stream: bool = False,
        **opts: Any,
    ) -> Any:
        body = _build_body(model=model, prompt=prompt, stream=stream, **opts)
        if stream:
            return self._t.stream_sse("/intelligence/completions")
        return _unwrap(
            await self._t.request(
                "POST", "/intelligence/completions", json_body=body
            )
        )

    async def chat(
        self,
        *,
        model: str,
        messages: List[Dict[str, Any]],
        stream: bool = False,
        **opts: Any,
    ) -> Any:
        body = _build_body(model=model, messages=messages, stream=stream, **opts)
        if stream:
            return self._t.stream_sse("/intelligence/chat/completions")
        return _unwrap(
            await self._t.request(
                "POST", "/intelligence/chat/completions", json_body=body
            )
        )
