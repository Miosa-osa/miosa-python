"""OpenComputers Clusters resource — sync and async variants."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING

from .types import Cluster, ClusterCreateParams, ClusterEvent, ClusterListResponse

if TYPE_CHECKING:
    from ..._http import AsyncTransport, SyncTransport


def _parse_cluster_event(raw: dict) -> ClusterEvent:
    data = raw.get("data", "")
    try:
        parsed = json.loads(data) if isinstance(data, str) and data else {}
    except (json.JSONDecodeError, ValueError):
        parsed = {"raw": data}
    return ClusterEvent.model_validate(parsed)


class ClustersResource:
    """Manage multi-host LLM inference clusters (sync)."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def list(self) -> ClusterListResponse:
        data = self._transport.request("GET", "/opencomputers/clusters")
        return ClusterListResponse.model_validate(data)

    def create(self, params: ClusterCreateParams) -> Cluster:
        data = self._transport.request(
            "POST", "/opencomputers/clusters", json_body=params.model_dump(exclude_none=True)
        )
        return Cluster.model_validate(data)

    def get(self, cluster_id: str) -> Cluster:
        data = self._transport.request("GET", f"/opencomputers/clusters/{cluster_id}")
        return Cluster.model_validate(data)

    def start(self, cluster_id: str) -> Cluster:
        data = self._transport.request("POST", f"/opencomputers/clusters/{cluster_id}/start")
        return Cluster.model_validate(data)

    def stop(self, cluster_id: str) -> Cluster:
        data = self._transport.request("POST", f"/opencomputers/clusters/{cluster_id}/stop")
        return Cluster.model_validate(data)

    def delete(self, cluster_id: str) -> None:
        self._transport.request("DELETE", f"/opencomputers/clusters/{cluster_id}")

    def events(self, cluster_id: str) -> Iterator[ClusterEvent]:
        for raw in self._transport.stream_sse(f"/opencomputers/clusters/{cluster_id}/events"):
            yield _parse_cluster_event(raw)


class AsyncClustersResource:
    """Manage multi-host LLM inference clusters (async)."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def list(self) -> ClusterListResponse:
        data = await self._transport.request("GET", "/opencomputers/clusters")
        return ClusterListResponse.model_validate(data)

    async def create(self, params: ClusterCreateParams) -> Cluster:
        data = await self._transport.request(
            "POST", "/opencomputers/clusters", json_body=params.model_dump(exclude_none=True)
        )
        return Cluster.model_validate(data)

    async def get(self, cluster_id: str) -> Cluster:
        data = await self._transport.request("GET", f"/opencomputers/clusters/{cluster_id}")
        return Cluster.model_validate(data)

    async def start(self, cluster_id: str) -> Cluster:
        data = await self._transport.request(
            "POST", f"/opencomputers/clusters/{cluster_id}/start"
        )
        return Cluster.model_validate(data)

    async def stop(self, cluster_id: str) -> Cluster:
        data = await self._transport.request(
            "POST", f"/opencomputers/clusters/{cluster_id}/stop"
        )
        return Cluster.model_validate(data)

    async def delete(self, cluster_id: str) -> None:
        await self._transport.request("DELETE", f"/opencomputers/clusters/{cluster_id}")

    async def events(self, cluster_id: str) -> AsyncIterator[ClusterEvent]:
        async for raw in self._transport.stream_sse(
            f"/opencomputers/clusters/{cluster_id}/events"
        ):
            yield _parse_cluster_event(raw)
