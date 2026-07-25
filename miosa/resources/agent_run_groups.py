"""Agent Run Groups — durable multi-agent orchestration groups."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any) -> Any:
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data


def _artifact_rows(data: Any) -> list[dict[str, Any]]:
    data = _unwrap(data)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        artifacts = data.get("artifacts") or data.get("items")
        return artifacts if isinstance(artifacts, list) else []
    return []


def _is_terminal_status(status: Any, terminal_statuses: tuple[str, ...]) -> bool:
    return isinstance(status, str) and status.lower() in terminal_statuses


def _body(**values: Any) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def _pick(entry: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in entry:
            return entry[key]
    return None


def _run_body(entry: dict[str, Any]) -> dict[str, Any]:
    return _body(
        prompt=entry.get("prompt"),
        target_kind=_pick(entry, "target_kind", "targetKind"),
        target_id=_pick(entry, "target_id", "targetId"),
        sandbox_id=_pick(entry, "sandbox_id", "sandboxId"),
        computer_id=_pick(entry, "computer_id", "computerId"),
        provider=entry.get("provider"),
        model=entry.get("model"),
        command=entry.get("command"),
        runtime_command=_pick(entry, "runtime_command", "runtimeCommand"),
        cwd=entry.get("cwd"),
        timeout=entry.get("timeout"),
        env=entry.get("env"),
        agent_runtime_profile_id=_pick(
            entry, "agent_runtime_profile_id", "agentRuntimeProfileId"
        ),
        agent_profile_id=_pick(entry, "agent_profile_id", "agentProfileId"),
        parent_agent_run_id=_pick(entry, "parent_agent_run_id", "parentAgentRunId"),
        orchestration_role=_pick(entry, "orchestration_role", "orchestrationRole"),
        skip_agent_runtime_profile=_pick(
            entry, "skip_agent_runtime_profile", "skipAgentRuntimeProfile"
        ),
        execution_packet=_pick(entry, "execution_packet", "executionPacket"),
        output_contract=_pick(entry, "output_contract", "outputContract"),
        approval_policy=_pick(entry, "approval_policy", "approvalPolicy"),
        capability_requirements=_pick(
            entry, "capability_requirements", "capabilityRequirements"
        ),
        metadata=entry.get("metadata"),
    )


class AgentRunGroups:
    """Durable groups for fanout and sub-agent orchestration."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def list(
        self,
        *,
        workspace_id: str | None = None,
        project_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        data = _unwrap(
            self._t.request(
                "GET",
                "/agent-run-groups",
                params=_body(
                    workspace_id=workspace_id,
                    project_id=project_id,
                    status=status,
                    limit=limit,
                ),
            )
        )
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            groups = data.get("groups") or data.get("items")
            return groups if isinstance(groups, list) else []
        return []

    def create(
        self,
        *,
        name: str,
        description: str | None = None,
        workspace_id: str | None = None,
        project_id: str | None = None,
        concurrency_limit: int | None = None,
        expected_runs: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return _unwrap(
            self._t.request(
                "POST",
                "/agent-run-groups",
                json_body=_body(
                    name=name,
                    description=description,
                    workspace_id=workspace_id,
                    project_id=project_id,
                    concurrency_limit=concurrency_limit,
                    expected_runs=expected_runs,
                    metadata=metadata,
                ),
            )
        )

    def get(self, group_id: str, *, include_runs: bool = False) -> dict[str, Any]:
        params = {"include": "runs"} if include_runs else None
        return _unwrap(self._t.request("GET", f"/agent-run-groups/{group_id}", params=params))

    def dispatch(
        self, group_id: str, runs: list[dict[str, Any]], *, async_: bool | None = None
    ) -> dict[str, Any]:
        return _unwrap(
            self._t.request(
                "POST",
                f"/agent-run-groups/{group_id}/dispatch",
                json_body=_body(runs=[_run_body(run) for run in runs], **{"async": async_}),
            )
        )

    def cancel(self, group_id: str) -> dict[str, Any]:
        return _unwrap(
            self._t.request("POST", f"/agent-run-groups/{group_id}/cancel", json_body={})
        )

    def events(self, group_id: str) -> list[dict[str, Any]]:
        data = _unwrap(self._t.request("GET", f"/agent-run-groups/{group_id}/events"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            events = data.get("events") or data.get("items")
            return events if isinstance(events, list) else []
        return []

    def stream_events(self, group_id: str) -> Iterator[dict[str, Any]]:
        yield from self._t.stream_sse(f"/agent-run-groups/{group_id}/events")

    def artifacts(self, group_id: str) -> list[dict[str, Any]]:
        group = self.get(group_id, include_runs=True)
        artifacts: list[dict[str, Any]] = []
        for run in group.get("runs") or []:
            if not isinstance(run, dict) or not run.get("id"):
                continue
            run_id = str(run["id"])
            for artifact in _artifact_rows(
                self._t.request("GET", f"/agent-runs/{run_id}/artifacts")
            ):
                artifacts.append(
                    {**artifact, "agent_run_id": artifact.get("agent_run_id") or run_id}
                )
        return artifacts

    def wait_for_completion(
        self,
        group_id: str,
        *,
        timeout: float = 900.0,
        poll_interval: float = 2.0,
        terminal_statuses: tuple[str, ...] = (
            "succeeded",
            "failed",
            "canceled",
            "cancelled",
        ),
        include_runs: bool = False,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout

        while True:
            group = self.get(group_id, include_runs=include_runs)
            if _is_terminal_status(group.get("status"), terminal_statuses):
                return group
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for agent run group {group_id}")
            time.sleep(min(poll_interval, max(0.0, deadline - time.monotonic())))


class AsyncAgentRunGroups:
    """Async Agent Run Groups API."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def list(
        self,
        *,
        workspace_id: str | None = None,
        project_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        data = _unwrap(
            await self._t.request(
                "GET",
                "/agent-run-groups",
                params=_body(
                    workspace_id=workspace_id,
                    project_id=project_id,
                    status=status,
                    limit=limit,
                ),
            )
        )
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            groups = data.get("groups") or data.get("items")
            return groups if isinstance(groups, list) else []
        return []

    async def create(
        self,
        *,
        name: str,
        description: str | None = None,
        workspace_id: str | None = None,
        project_id: str | None = None,
        concurrency_limit: int | None = None,
        expected_runs: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                "/agent-run-groups",
                json_body=_body(
                    name=name,
                    description=description,
                    workspace_id=workspace_id,
                    project_id=project_id,
                    concurrency_limit=concurrency_limit,
                    expected_runs=expected_runs,
                    metadata=metadata,
                ),
            )
        )

    async def get(self, group_id: str, *, include_runs: bool = False) -> dict[str, Any]:
        params = {"include": "runs"} if include_runs else None
        return _unwrap(
            await self._t.request("GET", f"/agent-run-groups/{group_id}", params=params)
        )

    async def dispatch(
        self, group_id: str, runs: list[dict[str, Any]], *, async_: bool | None = None
    ) -> dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                f"/agent-run-groups/{group_id}/dispatch",
                json_body=_body(runs=[_run_body(run) for run in runs], **{"async": async_}),
            )
        )

    async def cancel(self, group_id: str) -> dict[str, Any]:
        return _unwrap(
            await self._t.request("POST", f"/agent-run-groups/{group_id}/cancel", json_body={})
        )

    async def events(self, group_id: str) -> list[dict[str, Any]]:
        data = _unwrap(await self._t.request("GET", f"/agent-run-groups/{group_id}/events"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            events = data.get("events") or data.get("items")
            return events if isinstance(events, list) else []
        return []

    async def stream_events(self, group_id: str) -> AsyncIterator[dict[str, Any]]:
        async for event in self._t.stream_sse(f"/agent-run-groups/{group_id}/events"):
            yield event

    async def artifacts(self, group_id: str) -> list[dict[str, Any]]:
        group = await self.get(group_id, include_runs=True)
        artifacts: list[dict[str, Any]] = []
        for run in group.get("runs") or []:
            if not isinstance(run, dict) or not run.get("id"):
                continue
            run_id = str(run["id"])
            for artifact in _artifact_rows(
                await self._t.request("GET", f"/agent-runs/{run_id}/artifacts")
            ):
                artifacts.append(
                    {**artifact, "agent_run_id": artifact.get("agent_run_id") or run_id}
                )
        return artifacts

    async def wait_for_completion(
        self,
        group_id: str,
        *,
        timeout: float = 900.0,
        poll_interval: float = 2.0,
        terminal_statuses: tuple[str, ...] = (
            "succeeded",
            "failed",
            "canceled",
            "cancelled",
        ),
        include_runs: bool = False,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout

        while True:
            group = await self.get(group_id, include_runs=include_runs)
            if _is_terminal_status(group.get("status"), terminal_statuses):
                return group
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for agent run group {group_id}")
            await asyncio.sleep(min(poll_interval, max(0.0, deadline - time.monotonic())))
