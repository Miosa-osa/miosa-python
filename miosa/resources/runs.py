"""Runs - instruction dispatch into MIOSA sandbox and computer targets."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Any, TypedDict, cast

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


class _RequiredRunEvent(TypedDict):
    id: str
    run_id: str
    type: str


class RunEvent(_RequiredRunEvent, total=False):
    """A durable event emitted by a MIOSA run."""

    status: str | None
    message: str | None
    metadata: dict[str, Any]
    created_at: str | None


_RunEventList = list[RunEvent]


def _unwrap(data: Any) -> Any:
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data


def _is_terminal_status(status: Any, terminal_statuses: tuple[str, ...]) -> bool:
    return isinstance(status, str) and status.lower() in terminal_statuses


class Runs:
    """Prompt-dispatch API for sandbox and computer targets."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def list(
        self,
        *,
        target_kind: str | None = None,
        target_id: str | None = None,
        runtime_id: str | None = None,
        sandbox_id: str | None = None,
        computer_id: str | None = None,
        run_group_id: str | None = None,
        external_workspace_id: str | None = None,
        external_user_id: str | None = None,
        external_project_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        data = _unwrap(
            self._t.request(
                "GET",
                "/runs",
                params=_body(
                    target_kind=target_kind,
                    target_id=target_id,
                    runtime_id=runtime_id,
                    sandbox_id=sandbox_id,
                    computer_id=computer_id,
                    run_group_id=run_group_id,
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
        return _unwrap(self._t.request("GET", f"/runs/{run_id}"))

    def outputs(self, run_id: str) -> dict[str, Any]:
        data = _unwrap(self._t.request("GET", f"/runs/{run_id}/outputs"))
        return data if isinstance(data, dict) else {}

    def files(self, run_id: str) -> list[dict[str, Any]]:
        data = _unwrap(self._t.request("GET", f"/runs/{run_id}/files"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            files = data.get("files") or data.get("items")
            return files if isinstance(files, list) else []
        return []

    def stream_activity(self, run_id: str) -> Iterator[dict[str, Any]]:
        yield from self._t.stream_sse(f"/runs/{run_id}/activity")

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
                raise TimeoutError(f"Timed out waiting for run {run_id}")
            time.sleep(min(poll_interval, max(0.0, deadline - time.monotonic())))

    def download_file(self, run_id: str, file_id: str, *, inline: bool | None = None) -> bytes:
        params = {"disposition": "inline"} if inline else None
        response = self._t.request(
            "GET",
            f"/runs/{run_id}/files/{file_id}/download",
            params=params,
            raw_response=True,
        )
        return bytes(response.content)

    def messages(self, run_id: str) -> list[dict[str, Any]]:
        data = _unwrap(self._t.request("GET", f"/runs/{run_id}/messages"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            messages = data.get("messages") or data.get("items")
            return messages if isinstance(messages, list) else []
        return []

    def command_output(self, run_id: str) -> dict[str, Any]:
        data = _unwrap(self._t.request("GET", f"/runs/{run_id}/command-output"))
        return data if isinstance(data, dict) else {}

    def activity(self, run_id: str) -> list[dict[str, Any]]:
        data = _unwrap(self._t.request("GET", f"/runs/{run_id}/activity"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            activity = data.get("activity") or data.get("items")
            return activity if isinstance(activity, list) else []
        return []

    def events(
        self,
        run_id: str,
        *,
        after_id: str | None = None,
        limit: int | None = None,
    ) -> _RunEventList:
        data = _unwrap(
            self._t.request(
                "GET",
                f"/runs/{run_id}/events",
                params=_body(after_id=after_id, limit=limit),
            )
        )
        if isinstance(data, list):
            return cast(_RunEventList, data)
        if isinstance(data, dict):
            events = data.get("events") or data.get("items")
            return cast(_RunEventList, events) if isinstance(events, list) else []
        return []

    def previews(self, run_id: str) -> list[dict[str, Any]]:
        data = _unwrap(self._t.request("GET", f"/runs/{run_id}/previews"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            previews = data.get("previews") or data.get("items")
            return previews if isinstance(previews, list) else []
        return []

    def diagnostics(self, run_id: str) -> list[dict[str, Any]]:
        data = _unwrap(self._t.request("GET", f"/runs/{run_id}/diagnostics"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            diagnostics = data.get("diagnostics") or data.get("items")
            return diagnostics if isinstance(diagnostics, list) else []
        return []

    def run(
        self,
        *,
        instruction: str | None = None,
        target_kind: str | None = None,
        target_id: str | None = None,
        runtime_id: str | None = None,
        sandbox_id: str | None = None,
        computer_id: str | None = None,
        provider: str | None = None,
        runner: str | None = None,
        model: str | None = None,
        command: str | None = None,
        runtime_command: str | None = None,
        cwd: str | None = None,
        timeout: int | None = None,
        wait: bool | None = None,
        env: dict[str, str] | None = None,
        agent_runtime_profile_id: str | None = None,
        agent_profile_id: str | None = None,
        run_group_id: str | None = None,
        parent_run_id: str | None = None,
        orchestration_role: str | None = None,
        external_workspace_id: str | None = None,
        external_user_id: str | None = None,
        external_project_id: str | None = None,
        skip_agent_runtime_profile: bool | None = None,
        execution_packet: dict[str, Any] | None = None,
        expected_outputs: dict[str, Any] | None = None,
        approval_policy: dict[str, Any] | None = None,
        capability_requirements: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        body = _body(
            instruction=instruction,
            target_kind=target_kind,
            target_id=target_id,
            runtime_id=runtime_id,
            sandbox_id=sandbox_id,
            computer_id=computer_id,
            provider=provider,
            runner=runner,
            model=model,
            command=command,
            runtime_command=runtime_command,
            cwd=cwd,
            timeout=timeout,
            wait=wait,
            env=env,
            agent_runtime_profile_id=agent_runtime_profile_id,
            agent_profile_id=agent_profile_id,
            run_group_id=run_group_id,
            parent_run_id=parent_run_id,
            orchestration_role=orchestration_role,
            external_workspace_id=external_workspace_id,
            external_user_id=external_user_id,
            external_project_id=external_project_id,
            skip_agent_runtime_profile=skip_agent_runtime_profile,
            execution_packet=execution_packet,
            expected_outputs=expected_outputs,
            approval_policy=approval_policy,
            capability_requirements=capability_requirements,
            metadata=metadata,
        )
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        return _unwrap(
            self._t.request("POST", "/runs", json_body=body, headers=headers)
        )

    def cancel(self, run_id: str) -> dict[str, Any]:
        return _unwrap(
            self._t.request("POST", f"/runs/{run_id}/cancel", json_body={})
        )


class AsyncRuns:
    """Async Runs API."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def list(
        self,
        *,
        target_kind: str | None = None,
        target_id: str | None = None,
        runtime_id: str | None = None,
        sandbox_id: str | None = None,
        computer_id: str | None = None,
        run_group_id: str | None = None,
        external_workspace_id: str | None = None,
        external_user_id: str | None = None,
        external_project_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        data = _unwrap(
            await self._t.request(
                "GET",
                "/runs",
                params=_body(
                    target_kind=target_kind,
                    target_id=target_id,
                    runtime_id=runtime_id,
                    sandbox_id=sandbox_id,
                    computer_id=computer_id,
                    run_group_id=run_group_id,
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
        return _unwrap(await self._t.request("GET", f"/runs/{run_id}"))

    async def outputs(self, run_id: str) -> dict[str, Any]:
        data = _unwrap(await self._t.request("GET", f"/runs/{run_id}/outputs"))
        return data if isinstance(data, dict) else {}

    async def files(self, run_id: str) -> list[dict[str, Any]]:
        data = _unwrap(await self._t.request("GET", f"/runs/{run_id}/files"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            files = data.get("files") or data.get("items")
            return files if isinstance(files, list) else []
        return []

    async def stream_activity(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        async for event in self._t.stream_sse(f"/runs/{run_id}/activity"):
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
                raise TimeoutError(f"Timed out waiting for run {run_id}")
            await asyncio.sleep(min(poll_interval, max(0.0, deadline - time.monotonic())))

    async def download_file(
        self, run_id: str, file_id: str, *, inline: bool | None = None
    ) -> bytes:
        params = {"disposition": "inline"} if inline else None
        response = await self._t.request(
            "GET",
            f"/runs/{run_id}/files/{file_id}/download",
            params=params,
            raw_response=True,
        )
        return bytes(response.content)

    async def messages(self, run_id: str) -> list[dict[str, Any]]:
        data = _unwrap(await self._t.request("GET", f"/runs/{run_id}/messages"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            messages = data.get("messages") or data.get("items")
            return messages if isinstance(messages, list) else []
        return []

    async def command_output(self, run_id: str) -> dict[str, Any]:
        data = _unwrap(await self._t.request("GET", f"/runs/{run_id}/command-output"))
        return data if isinstance(data, dict) else {}

    async def activity(self, run_id: str) -> list[dict[str, Any]]:
        data = _unwrap(await self._t.request("GET", f"/runs/{run_id}/activity"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            activity = data.get("activity") or data.get("items")
            return activity if isinstance(activity, list) else []
        return []

    async def events(
        self,
        run_id: str,
        *,
        after_id: str | None = None,
        limit: int | None = None,
    ) -> _RunEventList:
        data = _unwrap(
            await self._t.request(
                "GET",
                f"/runs/{run_id}/events",
                params=_body(after_id=after_id, limit=limit),
            )
        )
        if isinstance(data, list):
            return cast(_RunEventList, data)
        if isinstance(data, dict):
            events = data.get("events") or data.get("items")
            return cast(_RunEventList, events) if isinstance(events, list) else []
        return []

    async def previews(self, run_id: str) -> list[dict[str, Any]]:
        data = _unwrap(await self._t.request("GET", f"/runs/{run_id}/previews"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            previews = data.get("previews") or data.get("items")
            return previews if isinstance(previews, list) else []
        return []

    async def diagnostics(self, run_id: str) -> list[dict[str, Any]]:
        data = _unwrap(await self._t.request("GET", f"/runs/{run_id}/diagnostics"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            diagnostics = data.get("diagnostics") or data.get("items")
            return diagnostics if isinstance(diagnostics, list) else []
        return []

    async def run(
        self,
        *,
        instruction: str | None = None,
        target_kind: str | None = None,
        target_id: str | None = None,
        runtime_id: str | None = None,
        sandbox_id: str | None = None,
        computer_id: str | None = None,
        provider: str | None = None,
        runner: str | None = None,
        model: str | None = None,
        command: str | None = None,
        runtime_command: str | None = None,
        cwd: str | None = None,
        timeout: int | None = None,
        wait: bool | None = None,
        env: dict[str, str] | None = None,
        agent_runtime_profile_id: str | None = None,
        agent_profile_id: str | None = None,
        run_group_id: str | None = None,
        parent_run_id: str | None = None,
        orchestration_role: str | None = None,
        external_workspace_id: str | None = None,
        external_user_id: str | None = None,
        external_project_id: str | None = None,
        skip_agent_runtime_profile: bool | None = None,
        execution_packet: dict[str, Any] | None = None,
        expected_outputs: dict[str, Any] | None = None,
        approval_policy: dict[str, Any] | None = None,
        capability_requirements: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        body = _body(
            instruction=instruction,
            target_kind=target_kind,
            target_id=target_id,
            runtime_id=runtime_id,
            sandbox_id=sandbox_id,
            computer_id=computer_id,
            provider=provider,
            runner=runner,
            model=model,
            command=command,
            runtime_command=runtime_command,
            cwd=cwd,
            timeout=timeout,
            wait=wait,
            env=env,
            agent_runtime_profile_id=agent_runtime_profile_id,
            agent_profile_id=agent_profile_id,
            run_group_id=run_group_id,
            parent_run_id=parent_run_id,
            orchestration_role=orchestration_role,
            external_workspace_id=external_workspace_id,
            external_user_id=external_user_id,
            external_project_id=external_project_id,
            skip_agent_runtime_profile=skip_agent_runtime_profile,
            execution_packet=execution_packet,
            expected_outputs=expected_outputs,
            approval_policy=approval_policy,
            capability_requirements=capability_requirements,
            metadata=metadata,
        )
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        return _unwrap(
            await self._t.request("POST", "/runs", json_body=body, headers=headers)
        )

    async def cancel(self, run_id: str) -> dict[str, Any]:
        return _unwrap(
            await self._t.request("POST", f"/runs/{run_id}/cancel", json_body={})
        )


def _body(**values: Any) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}
