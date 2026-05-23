"""Embeddings — OpenAI-compatible embedding vectors.

Routes are exposed under ``/api/v1/intelligence/embeddings`` and
require an ``mki_*`` intelligence key.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Union

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data",)) -> Any:
    # OpenAI envelope is {"object":"list","data":[...]} — we want the dict
    # itself, so this helper is intentionally permissive.
    if isinstance(data, dict) and "object" in data and "data" in data:
        return data
    return data


class Embeddings:
    """OpenAI-compatible embeddings."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def create(
        self,
        *,
        input: Union[str, List[str]],
        model: str,
        **opts: Any,
    ) -> Dict[str, Any]:
        """Create one or more embedding vectors (POST ``/intelligence/embeddings``).

        ``input`` may be a string or list of strings.
        """
        body = {"input": input, "model": model}
        body.update({k: v for k, v in opts.items() if v is not None})
        return _unwrap(
            self._t.request("POST", "/intelligence/embeddings", json_body=body)
        )


class AsyncEmbeddings:
    """Async embeddings."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def create(
        self,
        *,
        input: Union[str, List[str]],
        model: str,
        **opts: Any,
    ) -> Dict[str, Any]:
        body = {"input": input, "model": model}
        body.update({k: v for k, v in opts.items() if v is not None})
        return _unwrap(
            await self._t.request(
                "POST", "/intelligence/embeddings", json_body=body
            )
        )
