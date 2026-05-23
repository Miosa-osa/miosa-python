"""Firecracker microVM checkpoint (snapshot) management for a Computer.

Accessed via ``computer.checkpoints``. Supports create / list / get / delete
and restore, with optional SSE progress callbacks.

Example::

    snap = computer.checkpoints.create(comment="before upgrade")
    # ... do risky work ...
    restored = computer.checkpoints.restore(snap.id)
"""

from __future__ import annotations

import json as _json
from collections.abc import AsyncIterator, Iterator
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    List,
    Optional,
)

from ..types import Computer as ComputerModel
from ..types import SnapshotData, SnapshotProgressEvent

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport
    from .computer import AsyncComputer, Computer


ProgressCallback = Callable[[SnapshotProgressEvent], None]


def _unwrap(data: Any, key: str = "data") -> Any:
    if isinstance(data, dict) and key in data and len(data) <= 2:
        return data[key]
    return data


def _parse_sse_event(raw: dict) -> SnapshotProgressEvent:
    """Parse an SSE line dict (from ``stream_sse``) into a typed event."""
    payload = raw.get("data", "")
    if isinstance(payload, str):
        try:
            parsed = _json.loads(payload)
        except (ValueError, TypeError):
            parsed = {"status": payload}
    else:
        parsed = payload

    if not isinstance(parsed, dict):
        parsed = {"status": str(parsed)}
    parsed.setdefault("type", raw.get("type", "snapshot_progress"))
    parsed.setdefault("snapshot_id", parsed.get("snapshot_id", ""))
    parsed.setdefault("status", parsed.get("status", "unknown"))
    return SnapshotProgressEvent.model_validate(parsed)


# ───────────────────────────────────────────────────────────────────────────
# Sync
# ───────────────────────────────────────────────────────────────────────────

class Checkpoints:
    """Synchronous checkpoint management scoped to a single computer."""

    def __init__(self, transport: SyncTransport, computer_id: str) -> None:
        self._transport = transport
        self._computer_id = computer_id

    def _base(self) -> str:
        return f"/computers/{self._computer_id}/snapshots"

    def create(
        self,
        *,
        comment: Optional[str] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> SnapshotData:
        """Create a checkpoint of the running computer.

        The returned snapshot starts in ``creating`` state and progresses
        through ``uploading`` → ``ready`` asynchronously. Pass ``on_progress``
        to receive SSE progress events, or poll with :meth:`get`.
        """
        body: dict = {}
        if comment is not None:
            body["comment"] = comment
        raw = self._transport.request("POST", self._base(), json_body=body)
        snap = SnapshotData.model_validate(_unwrap(raw))

        if on_progress is not None:
            for event in self.events(snap.id):
                on_progress(event)
                if event.status in ("ready", "failed", "deleted"):
                    break

        return snap

    def list(self) -> List[SnapshotData]:
        """List all non-deleted checkpoints for this computer."""
        raw = self._transport.request("GET", self._base())
        items = _unwrap(raw, "data") if isinstance(raw, dict) else raw
        return [SnapshotData.model_validate(s) for s in (items or [])]

    def get(self, snapshot_id: str) -> SnapshotData:
        """Fetch a single checkpoint by id."""
        raw = self._transport.request("GET", f"{self._base()}/{snapshot_id}")
        return SnapshotData.model_validate(_unwrap(raw))

    def delete(self, snapshot_id: str) -> SnapshotData:
        """Delete a checkpoint. Returns the record with ``status='deleted'``."""
        raw = self._transport.request(
            "DELETE", f"{self._base()}/{snapshot_id}"
        )
        return SnapshotData.model_validate(_unwrap(raw))

    def restore(
        self,
        snapshot_id: str,
        *,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Computer:
        """Restore a checkpoint onto a fresh Computer.

        Returns a bound :class:`~miosa.resources.computer.Computer` for the
        newly-provisioned VM. Pass ``on_progress`` to follow restore SSE
        events synchronously.
        """
        from .computer import Computer

        raw = self._transport.request(
            "POST", f"/computers/{self._computer_id}/restore/{snapshot_id}"
        )
        # Server returns either {data: ComputerData} or
        # {data: ComputerData, snapshot: SnapshotData}.
        comp_data = raw.get("data") if isinstance(raw, dict) else raw
        if isinstance(comp_data, dict) and "id" not in comp_data:
            comp_data = comp_data.get("computer") or comp_data
        model = ComputerModel.model_validate(comp_data)

        if on_progress is not None:
            for event in self.events(snapshot_id):
                on_progress(event)
                if event.status in ("ready", "failed", "deleted"):
                    break

        return Computer(self._transport, model)

    def events(self, snapshot_id: str) -> Iterator[SnapshotProgressEvent]:
        """Iterate SSE progress events for ``snapshot_id``.

        Yields until the stream closes or a terminal status is reached
        (``ready`` / ``failed`` / ``deleted``).
        """
        path = f"{self._base()}/{snapshot_id}/events"
        for raw in self._transport.stream_sse(path):
            event = _parse_sse_event(raw)
            yield event
            if event.status in ("ready", "failed", "deleted"):
                return


# ───────────────────────────────────────────────────────────────────────────
# Async
# ───────────────────────────────────────────────────────────────────────────

class AsyncCheckpoints:
    """Asynchronous checkpoint management."""

    def __init__(self, transport: AsyncTransport, computer_id: str) -> None:
        self._transport = transport
        self._computer_id = computer_id

    def _base(self) -> str:
        return f"/computers/{self._computer_id}/snapshots"

    async def create(
        self,
        *,
        comment: Optional[str] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> SnapshotData:
        body: dict = {}
        if comment is not None:
            body["comment"] = comment
        raw = await self._transport.request("POST", self._base(), json_body=body)
        snap = SnapshotData.model_validate(_unwrap(raw))

        if on_progress is not None:
            async for event in self.events(snap.id):
                on_progress(event)
                if event.status in ("ready", "failed", "deleted"):
                    break

        return snap

    async def list(self) -> List[SnapshotData]:
        raw = await self._transport.request("GET", self._base())
        items = _unwrap(raw, "data") if isinstance(raw, dict) else raw
        return [SnapshotData.model_validate(s) for s in (items or [])]

    async def get(self, snapshot_id: str) -> SnapshotData:
        raw = await self._transport.request(
            "GET", f"{self._base()}/{snapshot_id}"
        )
        return SnapshotData.model_validate(_unwrap(raw))

    async def delete(self, snapshot_id: str) -> SnapshotData:
        raw = await self._transport.request(
            "DELETE", f"{self._base()}/{snapshot_id}"
        )
        return SnapshotData.model_validate(_unwrap(raw))

    async def restore(
        self,
        snapshot_id: str,
        *,
        on_progress: Optional[ProgressCallback] = None,
    ) -> AsyncComputer:
        from .computer import AsyncComputer

        raw = await self._transport.request(
            "POST", f"/computers/{self._computer_id}/restore/{snapshot_id}"
        )
        comp_data = raw.get("data") if isinstance(raw, dict) else raw
        if isinstance(comp_data, dict) and "id" not in comp_data:
            comp_data = comp_data.get("computer") or comp_data
        model = ComputerModel.model_validate(comp_data)

        if on_progress is not None:
            async for event in self.events(snapshot_id):
                on_progress(event)
                if event.status in ("ready", "failed", "deleted"):
                    break

        return AsyncComputer(self._transport, model)

    async def events(
        self, snapshot_id: str
    ) -> AsyncIterator[SnapshotProgressEvent]:
        path = f"{self._base()}/{snapshot_id}/events"
        async for raw in self._transport.stream_sse(path):
            event = _parse_sse_event(raw)
            yield event
            if event.status in ("ready", "failed", "deleted"):
                return
