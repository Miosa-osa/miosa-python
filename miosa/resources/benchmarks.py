"""Benchmarks — admin-triggered platform benchmark runs.

Routes live under ``/api/v1/admin/benchmarks/`` and require an admin
credential (``msk_a_*`` / ``msk_p_*`` or admin JWT). Available run
kinds include ``cold_boot``, ``fleet_routing``, ``concurrent_create``,
and ``full_e2e``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(
    data: Any, keys: tuple[str, ...] = ("data", "benchmarks", "samples", "items")
) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class Benchmarks:
    """Admin: trigger + inspect platform benchmark runs."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request("GET", "/admin/benchmarks", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def get(self, benchmark_id: str) -> Dict[str, Any]:
        return _unwrap(
            self._t.request("GET", f"/admin/benchmarks/{benchmark_id}")
        )

    def create(self, **attrs: Any) -> Dict[str, Any]:
        """Start a new benchmark run — pass ``kind=`` and run-specific options."""
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(self._t.request("POST", "/admin/benchmarks", json_body=body))

    def cancel(self, benchmark_id: str) -> Dict[str, Any]:
        return _unwrap(
            self._t.request("POST", f"/admin/benchmarks/{benchmark_id}/cancel")
        )

    def samples(self, benchmark_id: str, **filters: Any) -> List[Dict[str, Any]]:
        """Return per-iteration timing samples for a benchmark run."""
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request(
            "GET",
            f"/admin/benchmarks/{benchmark_id}/samples",
            params=params or None,
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def compare(self, left_id: str, right_id: str, **opts: Any) -> Dict[str, Any]:
        """Compare two benchmark runs (POST ``/admin/benchmarks/compare``)."""
        body = {"left_id": left_id, "right_id": right_id}
        body.update({k: v for k, v in opts.items() if v is not None})
        return _unwrap(
            self._t.request("POST", "/admin/benchmarks/compare", json_body=body)
        )


class AsyncBenchmarks:
    """Async benchmarks."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request(
            "GET", "/admin/benchmarks", params=params or None
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def get(self, benchmark_id: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request("GET", f"/admin/benchmarks/{benchmark_id}")
        )

    async def create(self, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            await self._t.request("POST", "/admin/benchmarks", json_body=body)
        )

    async def cancel(self, benchmark_id: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST", f"/admin/benchmarks/{benchmark_id}/cancel"
            )
        )

    async def samples(
        self, benchmark_id: str, **filters: Any
    ) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request(
            "GET",
            f"/admin/benchmarks/{benchmark_id}/samples",
            params=params or None,
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def compare(
        self, left_id: str, right_id: str, **opts: Any
    ) -> Dict[str, Any]:
        body = {"left_id": left_id, "right_id": right_id}
        body.update({k: v for k, v in opts.items() if v is not None})
        return _unwrap(
            await self._t.request(
                "POST", "/admin/benchmarks/compare", json_body=body
            )
        )
