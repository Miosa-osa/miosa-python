"""OpenComputers Files resource — sync and async variants."""

from __future__ import annotations

from typing import TYPE_CHECKING, Union

from .types import FsEntry, FsListResponse, FsStat

if TYPE_CHECKING:
    from ..._http import AsyncTransport, SyncTransport


class OcFilesResource:
    """Direct file-system access on a remote host (sync)."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def _base(self, host_id: str) -> str:
        return f"/opencomputers/hosts/{host_id}/fs"

    def list(self, host_id: str, path: str) -> FsListResponse:
        """List directory entries at ``path``."""
        data = self._transport.request("GET", self._base(host_id), params={"path": path})
        return FsListResponse.model_validate(data)

    def stat(self, host_id: str, path: str) -> FsStat:
        """Stat a path (lstat semantics — does not follow symlinks)."""
        data = self._transport.request(
            "GET", f"{self._base(host_id)}/stat", params={"path": path}
        )
        return FsStat.model_validate(data)

    def download(self, host_id: str, path: str) -> bytes:
        """Download a file. Returns raw bytes."""
        response = self._transport.request(
            "GET",
            f"{self._base(host_id)}/download",
            params={"path": path},
            raw_response=True,
        )
        return response.content

    def upload(
        self,
        host_id: str,
        remote_path: str,
        content: Union[bytes, str],
        filename: str = "file",
    ) -> FsEntry:
        """Upload content to ``remote_path`` on the host."""
        if isinstance(content, str):
            content = content.encode()
        data = self._transport.request(
            "POST",
            f"{self._base(host_id)}/upload",
            files={"file": (filename, content, "application/octet-stream")},
            data={"path": remote_path},
        )
        return FsEntry.model_validate(data)

    def delete(self, host_id: str, path: str, *, recursive: bool = False) -> None:
        """Delete a file or directory."""
        self._transport.request(
            "DELETE", self._base(host_id), params={"path": path, "recursive": str(recursive).lower()}
        )

    def mkdir(self, host_id: str, path: str) -> None:
        """Create a directory (including missing parents)."""
        self._transport.request(
            "POST", f"{self._base(host_id)}/mkdir", json_body={"path": path}
        )


class AsyncOcFilesResource:
    """Direct file-system access on a remote host (async)."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    def _base(self, host_id: str) -> str:
        return f"/opencomputers/hosts/{host_id}/fs"

    async def list(self, host_id: str, path: str) -> FsListResponse:
        data = await self._transport.request("GET", self._base(host_id), params={"path": path})
        return FsListResponse.model_validate(data)

    async def stat(self, host_id: str, path: str) -> FsStat:
        data = await self._transport.request(
            "GET", f"{self._base(host_id)}/stat", params={"path": path}
        )
        return FsStat.model_validate(data)

    async def download(self, host_id: str, path: str) -> bytes:
        response = await self._transport.request(
            "GET",
            f"{self._base(host_id)}/download",
            params={"path": path},
            raw_response=True,
        )
        return response.content

    async def upload(
        self,
        host_id: str,
        remote_path: str,
        content: Union[bytes, str],
        filename: str = "file",
    ) -> FsEntry:
        if isinstance(content, str):
            content = content.encode()
        data = await self._transport.request(
            "POST",
            f"{self._base(host_id)}/upload",
            files={"file": (filename, content, "application/octet-stream")},
            data={"path": remote_path},
        )
        return FsEntry.model_validate(data)

    async def delete(self, host_id: str, path: str, *, recursive: bool = False) -> None:
        await self._transport.request(
            "DELETE",
            self._base(host_id),
            params={"path": path, "recursive": str(recursive).lower()},
        )

    async def mkdir(self, host_id: str, path: str) -> None:
        await self._transport.request(
            "POST", f"{self._base(host_id)}/mkdir", json_body={"path": path}
        )
