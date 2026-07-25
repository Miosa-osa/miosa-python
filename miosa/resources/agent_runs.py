"""Agent Runs — prompt dispatch into MIOSA sandbox and computer targets."""

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


def _is_terminal_status(status: Any, terminal_statuses: tuple[str, ...]) -> bool:
    return isinstance(status, str) and status.lower() in terminal_statuses


class AgentRuns:
    """Prompt-dispatch API for sandbox and computer targets."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def list(
        self,
        *,
        target_kind: str | None = None,
        target_id: str | None = None,
        sandbox_id: str | None = None,
        computer_id: str | None = None,
        agent_run_group_id: str | None = None,
        external_workspace_id: str | None = None,
        external_user_id: str | None = None,
        external_project_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        data = _unwrap(
            self._t.request(
                "GET",
                "/agent-runs",
                params=_body(
                    target_kind=target_kind,
                    target_id=target_id,
                    sandbox_id=sandbox_id,
                    computer_id=computer_id,
                    agent_run_group_id=agent_run_group_id,
                    external_workspace_id=external_workspace_id,
                    external_user_id=external_user_id,
                    external_project_id=external_project_id,
                    status=status,
                ),
            )
        )
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            runs = data.get("runs") or data.get("items")
            return runs if isinstance(runs, list) else []
        return []

    def get(self, run_id: str) -> dict[str, Any]:
        return _unwrap(self._t.request("GET", f"/agent-runs/{run_id}"))

    def artifacts(self, run_id: str) -> list[dict[str, Any]]:
        data = _unwrap(self._t.request("GET", f"/agent-runs/{run_id}/artifacts"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            artifacts = data.get("artifacts") or data.get("items")
            return artifacts if isinstance(artifacts, list) else []
        return []

    def events(self, run_id: str) -> list[dict[str, Any]]:
        data = _unwrap(self._t.request("GET", f"/agent-runs/{run_id}/events"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            events = data.get("events") or data.get("items")
            return events if isinstance(events, list) else []
        return []

    def stream_events(self, run_id: str) -> Iterator[dict[str, Any]]:
        yield from self._t.stream_sse(f"/agent-runs/{run_id}/events")

    def wait_for_completion(
        self,
        run_id: str,
        *,
        timeout: float = 900.0,
        poll_interval: float = 2.0,
        terminal_statuses: tuple[str, ...] = (
            "succeeded",
            "failed",
            "canceled",
            "cancelled",
        ),
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout

        while True:
            run = self.get(run_id)
            if _is_terminal_status(run.get("status"), terminal_statuses):
                return run
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for agent run {run_id}")
            time.sleep(min(poll_interval, max(0.0, deadline - time.monotonic())))

    def download_artifact(
        self, run_id: str, artifact_id: str, *, inline: bool | None = None
    ) -> bytes:
        params = {"disposition": "inline"} if inline else None
        response = self._t.request(
            "GET",
            f"/agent-runs/{run_id}/artifacts/{artifact_id}/download",
            params=params,
            raw_response=True,
        )
        return bytes(response.content)

    def run(
        self,
        *,
        prompt: str,
        target_kind: str | None = None,
        target_id: str | None = None,
        sandbox_id: str | None = None,
        computer_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        command: str | None = None,
        runtime_command: str | None = None,
        cwd: str | None = None,
        timeout: int | None = None,
        wait: bool | None = None,
        env: dict[str, str] | None = None,
        output_format: str | None = None,
        resume_session_id: str | None = None,
        json: bool | None = None,
        output_schema: str | None = None,
        image: str | None = None,
        agent_runtime_profile_id: str | None = None,
        agent_profile_id: str | None = None,
        agent_run_group_id: str | None = None,
        parent_agent_run_id: str | None = None,
        orchestration_role: str | None = None,
        external_workspace_id: str | None = None,
        external_user_id: str | None = None,
        external_project_id: str | None = None,
        skip_agent_runtime_profile: bool | None = None,
        execution_packet: dict[str, Any] | None = None,
        output_contract: dict[str, Any] | None = None,
        approval_policy: dict[str, Any] | None = None,
        capability_requirements: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = _body(
            prompt=prompt,
            target_kind=target_kind,
            target_id=target_id,
            sandbox_id=sandbox_id,
            computer_id=computer_id,
            provider=provider,
            model=model,
            command=command,
            runtime_command=runtime_command,
            cwd=cwd,
            timeout=timeout,
            wait=wait,
            env=env,
            output_format=output_format,
            resume_session_id=resume_session_id,
            json=json,
            output_schema=output_schema,
            image=image,
            agent_runtime_profile_id=agent_runtime_profile_id,
            agent_profile_id=agent_profile_id,
            agent_run_group_id=agent_run_group_id,
            parent_agent_run_id=parent_agent_run_id,
            orchestration_role=orchestration_role,
            external_workspace_id=external_workspace_id,
            external_user_id=external_user_id,
            external_project_id=external_project_id,
            skip_agent_runtime_profile=skip_agent_runtime_profile,
            execution_packet=execution_packet,
            output_contract=output_contract,
            approval_policy=approval_policy,
            capability_requirements=capability_requirements,
            metadata=metadata,
        )
        return _unwrap(self._t.request("POST", "/agent-runs", json_body=body))

    def cancel(self, run_id: str) -> dict[str, Any]:
        return _unwrap(
            self._t.request("POST", f"/agent-runs/{run_id}/cancel", json_body={})
        )


class AsyncAgentRuns:
    """Async Agent Runs API."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def list(
        self,
        *,
        target_kind: str | None = None,
        target_id: str | None = None,
        sandbox_id: str | None = None,
        computer_id: str | None = None,
        agent_run_group_id: str | None = None,
        external_workspace_id: str | None = None,
        external_user_id: str | None = None,
        external_project_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        data = _unwrap(
            await self._t.request(
                "GET",
                "/agent-runs",
                params=_body(
                    target_kind=target_kind,
                    target_id=target_id,
                    sandbox_id=sandbox_id,
                    computer_id=computer_id,
                    agent_run_group_id=agent_run_group_id,
                    external_workspace_id=external_workspace_id,
                    external_user_id=external_user_id,
                    external_project_id=external_project_id,
                    status=status,
                ),
            )
        )
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            runs = data.get("runs") or data.get("items")
            return runs if isinstance(runs, list) else []
        return []

    async def get(self, run_id: str) -> dict[str, Any]:
        return _unwrap(await self._t.request("GET", f"/agent-runs/{run_id}"))

    async def artifacts(self, run_id: str) -> list[dict[str, Any]]:
        data = _unwrap(await self._t.request("GET", f"/agent-runs/{run_id}/artifacts"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            artifacts = data.get("artifacts") or data.get("items")
            return artifacts if isinstance(artifacts, list) else []
        return []

    async def events(self, run_id: str) -> list[dict[str, Any]]:
        data = _unwrap(await self._t.request("GET", f"/agent-runs/{run_id}/events"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            events = data.get("events") or data.get("items")
            return events if isinstance(events, list) else []
        return []

    async def stream_events(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        async for event in self._t.stream_sse(f"/agent-runs/{run_id}/events"):
            yield event

    async def wait_for_completion(
        self,
        run_id: str,
        *,
        timeout: float = 900.0,
        poll_interval: float = 2.0,
        terminal_statuses: tuple[str, ...] = (
            "succeeded",
            "failed",
            "canceled",
            "cancelled",
        ),
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout

        while True:
            run = await self.get(run_id)
            if _is_terminal_status(run.get("status"), terminal_statuses):
                return run
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for agent run {run_id}")
            await asyncio.sleep(min(poll_interval, max(0.0, deadline - time.monotonic())))

    async def download_artifact(
        self, run_id: str, artifact_id: str, *, inline: bool | None = None
    ) -> bytes:
        params = {"disposition": "inline"} if inline else None
        response = await self._t.request(
            "GET",
            f"/agent-runs/{run_id}/artifacts/{artifact_id}/download",
            params=params,
            raw_response=True,
        )
        return bytes(response.content)

    async def run(
        self,
        *,
        prompt: str,
        target_kind: str | None = None,
        target_id: str | None = None,
        sandbox_id: str | None = None,
        computer_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        command: str | None = None,
        runtime_command: str | None = None,
        cwd: str | None = None,
        timeout: int | None = None,
        wait: bool | None = None,
        env: dict[str, str] | None = None,
        output_format: str | None = None,
        resume_session_id: str | None = None,
        json: bool | None = None,
        output_schema: str | None = None,
        image: str | None = None,
        agent_runtime_profile_id: str | None = None,
        agent_profile_id: str | None = None,
        agent_run_group_id: str | None = None,
        parent_agent_run_id: str | None = None,
        orchestration_role: str | None = None,
        external_workspace_id: str | None = None,
        external_user_id: str | None = None,
        external_project_id: str | None = None,
        skip_agent_runtime_profile: bool | None = None,
        execution_packet: dict[str, Any] | None = None,
        output_contract: dict[str, Any] | None = None,
        approval_policy: dict[str, Any] | None = None,
        capability_requirements: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = _body(
            prompt=prompt,
            target_kind=target_kind,
            target_id=target_id,
            sandbox_id=sandbox_id,
            computer_id=computer_id,
            provider=provider,
            model=model,
            command=command,
            runtime_command=runtime_command,
            cwd=cwd,
            timeout=timeout,
            wait=wait,
            env=env,
            output_format=output_format,
            resume_session_id=resume_session_id,
            json=json,
            output_schema=output_schema,
            image=image,
            agent_runtime_profile_id=agent_runtime_profile_id,
            agent_profile_id=agent_profile_id,
            agent_run_group_id=agent_run_group_id,
            parent_agent_run_id=parent_agent_run_id,
            orchestration_role=orchestration_role,
            external_workspace_id=external_workspace_id,
            external_user_id=external_user_id,
            external_project_id=external_project_id,
            skip_agent_runtime_profile=skip_agent_runtime_profile,
            execution_packet=execution_packet,
            output_contract=output_contract,
            approval_policy=approval_policy,
            capability_requirements=capability_requirements,
            metadata=metadata,
        )
        return _unwrap(await self._t.request("POST", "/agent-runs", json_body=body))

    async def cancel(self, run_id: str) -> dict[str, Any]:
        return _unwrap(
            await self._t.request("POST", f"/agent-runs/{run_id}/cancel", json_body={})
        )


def _body(**values: Any) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}
