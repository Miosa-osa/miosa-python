"""OpenComputers Jobs resource — sync and async variants."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING

from .types import Job, JobEvent, JobListResponse, JobRunParams

if TYPE_CHECKING:
    from ..._http import AsyncTransport, SyncTransport


def _parse_event(raw: dict) -> JobEvent:
    """Parse the SSE dict from the transport into a JobEvent."""
    data = raw.get("data", "")
    try:
        parsed = json.loads(data) if isinstance(data, str) and data else {}
    except (json.JSONDecodeError, ValueError):
        parsed = {"raw": data}
    return JobEvent.model_validate(parsed)


class JobsResource:
    """Execute and manage jobs on a remote host (sync)."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def run(self, host_id: str, params: JobRunParams) -> Job:
        """Dispatch a command to run on the host."""
        data = self._transport.request(
            "POST",
            f"/opencomputers/hosts/{host_id}/exec",
            json_body=params.model_dump(exclude_none=True),
        )
        return Job.model_validate(data)

    def list(self, host_id: str) -> JobListResponse:
        """List all jobs for a host."""
        data = self._transport.request("GET", f"/opencomputers/hosts/{host_id}/exec")
        return JobListResponse.model_validate(data)

    def get(self, host_id: str, job_id: str) -> Job:
        """Fetch the current state of a job."""
        data = self._transport.request("GET", f"/opencomputers/hosts/{host_id}/exec/{job_id}")
        return Job.model_validate(data)

    def stream(self, host_id: str, job_id: str) -> Iterator[JobEvent]:
        """Stream live output events from a running job."""
        for raw in self._transport.stream_sse(
            f"/opencomputers/hosts/{host_id}/exec/{job_id}/stream"
        ):
            yield _parse_event(raw)

    def cancel(self, host_id: str, job_id: str) -> None:
        """Cancel a running or queued job."""
        self._transport.request("DELETE", f"/opencomputers/hosts/{host_id}/exec/{job_id}")


class AsyncJobsResource:
    """Execute and manage jobs on a remote host (async)."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def run(self, host_id: str, params: JobRunParams) -> Job:
        data = await self._transport.request(
            "POST",
            f"/opencomputers/hosts/{host_id}/exec",
            json_body=params.model_dump(exclude_none=True),
        )
        return Job.model_validate(data)

    async def list(self, host_id: str) -> JobListResponse:
        data = await self._transport.request("GET", f"/opencomputers/hosts/{host_id}/exec")
        return JobListResponse.model_validate(data)

    async def get(self, host_id: str, job_id: str) -> Job:
        data = await self._transport.request(
            "GET", f"/opencomputers/hosts/{host_id}/exec/{job_id}"
        )
        return Job.model_validate(data)

    async def stream(self, host_id: str, job_id: str) -> AsyncIterator[JobEvent]:
        async for raw in self._transport.stream_sse(
            f"/opencomputers/hosts/{host_id}/exec/{job_id}/stream"
        ):
            yield _parse_event(raw)

    async def cancel(self, host_id: str, job_id: str) -> None:
        await self._transport.request(
            "DELETE", f"/opencomputers/hosts/{host_id}/exec/{job_id}"
        )
