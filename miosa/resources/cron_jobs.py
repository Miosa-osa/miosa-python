"""Cron jobs — scheduled work."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data", "cron_jobs", "executions", "items")) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class CronJobs:
    """Cron jobs — CRUD + pause/resume + run-now + execution history."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._t.request("GET", "/cron-jobs", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def get(self, job_id: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("GET", f"/cron-jobs/{job_id}"))

    def create(self, *, name: str, schedule: str, **attrs: Any) -> Dict[str, Any]:
        """Create a cron job.

        :param schedule: Cron expression (e.g. ``"0 4 * * *"``).
        """
        body = {
            "name": name,
            "schedule": schedule,
            **{k: v for k, v in attrs.items() if v is not None},
        }
        return _unwrap(self._t.request("POST", "/cron-jobs", json_body=body))

    def update(self, job_id: str, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            self._t.request("PATCH", f"/cron-jobs/{job_id}", json_body=body)
        )

    def delete(self, job_id: str) -> None:
        self._t.request("DELETE", f"/cron-jobs/{job_id}")

    # ── Control ────────────────────────────────────────────────────────

    def pause(self, job_id: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("POST", f"/cron-jobs/{job_id}/pause"))

    def resume(self, job_id: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("POST", f"/cron-jobs/{job_id}/resume"))

    def run_now(self, job_id: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("POST", f"/cron-jobs/{job_id}/run-now"))

    # ── Execution history ─────────────────────────────────────────────

    def list_executions(self, job_id: str) -> List[Dict[str, Any]]:
        data = self._t.request("GET", f"/cron-jobs/{job_id}/executions")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def get_execution(self, job_id: str, execution_id: str) -> Dict[str, Any]:
        return _unwrap(
            self._t.request(
                "GET", f"/cron-jobs/{job_id}/executions/{execution_id}"
            )
        )


class AsyncCronJobs:
    """Async cron jobs."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        data = await self._t.request("GET", "/cron-jobs", params=params or None)
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def get(self, job_id: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", f"/cron-jobs/{job_id}"))

    async def create(self, *, name: str, schedule: str, **attrs: Any) -> Dict[str, Any]:
        body = {
            "name": name,
            "schedule": schedule,
            **{k: v for k, v in attrs.items() if v is not None},
        }
        return _unwrap(await self._t.request("POST", "/cron-jobs", json_body=body))

    async def update(self, job_id: str, **attrs: Any) -> Dict[str, Any]:
        body = {k: v for k, v in attrs.items() if v is not None}
        return _unwrap(
            await self._t.request("PATCH", f"/cron-jobs/{job_id}", json_body=body)
        )

    async def delete(self, job_id: str) -> None:
        await self._t.request("DELETE", f"/cron-jobs/{job_id}")

    async def pause(self, job_id: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("POST", f"/cron-jobs/{job_id}/pause"))

    async def resume(self, job_id: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("POST", f"/cron-jobs/{job_id}/resume"))

    async def run_now(self, job_id: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("POST", f"/cron-jobs/{job_id}/run-now"))

    async def list_executions(self, job_id: str) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", f"/cron-jobs/{job_id}/executions")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def get_execution(self, job_id: str, execution_id: str) -> Dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "GET", f"/cron-jobs/{job_id}/executions/{execution_id}"
            )
        )
