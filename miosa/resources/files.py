"""File management resource — upload, download, list, export, delete."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional, Union

from ..types import ActionResponse, DirEntry, FileInfo, FileStat

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _dir_entries(data: Any) -> list[dict]:
    """Extract ``entries`` from various response envelope shapes."""
    if isinstance(data, dict):
        inner = data.get("data", data)
        if isinstance(inner, dict):
            return inner.get("entries") or []
    return []


def _mode_str(mode: Optional[Union[int, str]], default: str = "0755") -> str:
    if mode is None:
        return default
    if isinstance(mode, int):
        return format(mode, "04o")
    return mode


class FilesResource:
    """Synchronous file operations on a computer."""

    def __init__(self, transport: SyncTransport, computer_id: str) -> None:
        self._transport = transport
        self._computer_id = computer_id

    def _path(self, action: str = "") -> str:
        base = f"/computers/{self._computer_id}/files"
        return f"{base}/{action}" if action else base

    def upload(
        self,
        local_path: Union[str, Path],
        remote_path: str,
    ) -> ActionResponse:
        """Upload a local file to the computer."""
        local = Path(local_path)
        with open(local, "rb") as f:
            files = {"file": (local.name, f)}
            data = {"path": remote_path}
            resp = self._transport.request(
                "POST",
                self._path("upload"),
                files=files,
                data=data,
            )
        return ActionResponse.model_validate(resp)

    def download(self, remote_path: str) -> bytes:
        """Download a file from the computer as bytes."""
        resp = self._transport.request(
            "GET",
            self._path("download"),
            params={"path": remote_path},
            raw_response=True,
        )
        if resp.status_code >= 400:
            from .._http import _parse_body
            from ..errors import _extract_request_id, raise_for_status
            body = _parse_body(resp)
            raise_for_status(resp.status_code, body, _extract_request_id(resp))
        return resp.content

    def list(self, path: Optional[str] = None) -> List[FileInfo]:
        """List files at *path* on the computer."""
        params = {"path": path} if path else None
        data = self._transport.request("GET", self._path(), params=params)
        if isinstance(data, dict) and "data" in data:
            return [FileInfo.model_validate(f) for f in data["data"]]
        if isinstance(data, list):
            return [FileInfo.model_validate(f) for f in data]
        return []

    def export(self, remote_path: str) -> ActionResponse:
        """Export a file from the computer."""
        data = self._transport.request(
            "POST",
            self._path("export"),
            json_body={"path": remote_path},
        )
        return ActionResponse.model_validate(data)

    def delete(self, remote_path: str) -> ActionResponse:
        """Delete a file on the computer."""
        data = self._transport.request(
            "DELETE",
            self._path(),
            json_body={"path": remote_path},
        )
        return ActionResponse.model_validate(data)

    # ── stdlib-parity methods ──────────────────────────────────────────────

    def stat(self, path: str) -> FileStat:
        """Stat a path (lstat semantics — does not follow symlinks)."""
        data = self._transport.request(
            "POST", self._path("stat"), json_body={"path": path}
        )
        payload = data.get("data", data) if isinstance(data, dict) else data
        return FileStat.model_validate(payload)

    def mkdir(
        self,
        path: str,
        *,
        recursive: bool = True,
        mode: Optional[Union[int, str]] = None,
    ) -> None:
        """Create a directory. ``recursive=True`` creates parents (mkdir -p)."""
        self._transport.request(
            "POST",
            self._path("mkdir"),
            json_body={
                "path": path,
                "recursive": recursive,
                "mode": _mode_str(mode),
            },
        )

    def rename(self, source: str, dest: str) -> None:
        """Rename / move a path inside the computer."""
        self._transport.request(
            "POST", self._path("rename"), json_body={"from": source, "to": dest}
        )

    def copy(self, source: str, dest: str, *, recursive: bool = False) -> None:
        """Copy a file or (when ``recursive=True``) a directory tree."""
        self._transport.request(
            "POST",
            self._path("copy"),
            json_body={"from": source, "to": dest, "recursive": recursive},
        )

    def chmod(self, path: str, mode: Union[int, str]) -> None:
        """Change a path's Unix mode bits (``0o755`` or ``"0755"``)."""
        self._transport.request(
            "POST",
            self._path("chmod"),
            json_body={"path": path, "mode": _mode_str(mode, default="0644")},
        )

    def readdir(self, path: str) -> List[DirEntry]:
        """Rich directory listing — returns :class:`DirEntry` objects."""
        data = self._transport.request(
            "GET", self._path("readdir"), params={"path": path}
        )
        return [DirEntry.model_validate(e) for e in _dir_entries(data)]

    # ── text helpers ───────────────────────────────────────────────────────

    def write_file(self, path: str, content: Union[str, bytes]) -> None:
        """Write bytes/UTF-8 text to ``path`` via the JSON ``/write`` endpoint."""
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content
        encoded = base64.b64encode(content_bytes).decode("ascii")
        self._transport.request(
            "POST",
            self._path("write"),
            json_body={"path": path, "content_base64": encoded},
        )

    def read_file(self, path: str) -> str:
        """Read a file and decode as UTF-8. Use :meth:`download` for raw bytes."""
        return self.download(path).decode("utf-8")


class AsyncFilesResource:
    """Asynchronous file operations on a computer."""

    def __init__(self, transport: AsyncTransport, computer_id: str) -> None:
        self._transport = transport
        self._computer_id = computer_id

    def _path(self, action: str = "") -> str:
        base = f"/computers/{self._computer_id}/files"
        return f"{base}/{action}" if action else base

    async def upload(
        self,
        local_path: Union[str, Path],
        remote_path: str,
    ) -> ActionResponse:
        local = Path(local_path)
        with open(local, "rb") as f:
            files = {"file": (local.name, f)}
            data = {"path": remote_path}
            resp = await self._transport.request(
                "POST",
                self._path("upload"),
                files=files,
                data=data,
            )
        return ActionResponse.model_validate(resp)

    async def download(self, remote_path: str) -> bytes:
        resp = await self._transport.request(
            "GET",
            self._path("download"),
            params={"path": remote_path},
            raw_response=True,
        )
        if resp.status_code >= 400:
            from .._http import _parse_body
            from ..errors import _extract_request_id, raise_for_status
            body = _parse_body(resp)
            raise_for_status(resp.status_code, body, _extract_request_id(resp))
        return resp.content

    async def list(self, path: Optional[str] = None) -> List[FileInfo]:
        params = {"path": path} if path else None
        data = await self._transport.request("GET", self._path(), params=params)
        if isinstance(data, dict) and "data" in data:
            return [FileInfo.model_validate(f) for f in data["data"]]
        if isinstance(data, list):
            return [FileInfo.model_validate(f) for f in data]
        return []

    async def export(self, remote_path: str) -> ActionResponse:
        data = await self._transport.request(
            "POST",
            self._path("export"),
            json_body={"path": remote_path},
        )
        return ActionResponse.model_validate(data)

    async def delete(self, remote_path: str) -> ActionResponse:
        data = await self._transport.request(
            "DELETE",
            self._path(),
            json_body={"path": remote_path},
        )
        return ActionResponse.model_validate(data)

    # ── stdlib-parity methods ──────────────────────────────────────────────

    async def stat(self, path: str) -> FileStat:
        data = await self._transport.request(
            "POST", self._path("stat"), json_body={"path": path}
        )
        payload = data.get("data", data) if isinstance(data, dict) else data
        return FileStat.model_validate(payload)

    async def mkdir(
        self,
        path: str,
        *,
        recursive: bool = True,
        mode: Optional[Union[int, str]] = None,
    ) -> None:
        await self._transport.request(
            "POST",
            self._path("mkdir"),
            json_body={
                "path": path,
                "recursive": recursive,
                "mode": _mode_str(mode),
            },
        )

    async def rename(self, source: str, dest: str) -> None:
        await self._transport.request(
            "POST", self._path("rename"), json_body={"from": source, "to": dest}
        )

    async def copy(
        self, source: str, dest: str, *, recursive: bool = False
    ) -> None:
        await self._transport.request(
            "POST",
            self._path("copy"),
            json_body={"from": source, "to": dest, "recursive": recursive},
        )

    async def chmod(self, path: str, mode: Union[int, str]) -> None:
        await self._transport.request(
            "POST",
            self._path("chmod"),
            json_body={"path": path, "mode": _mode_str(mode, default="0644")},
        )

    async def readdir(self, path: str) -> List[DirEntry]:
        data = await self._transport.request(
            "GET", self._path("readdir"), params={"path": path}
        )
        return [DirEntry.model_validate(e) for e in _dir_entries(data)]

    async def write_file(self, path: str, content: Union[str, bytes]) -> None:
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content
        encoded = base64.b64encode(content_bytes).decode("ascii")
        await self._transport.request(
            "POST",
            self._path("write"),
            json_body={"path": path, "content_base64": encoded},
        )

    async def read_file(self, path: str) -> str:
        raw = await self.download(path)
        return raw.decode("utf-8")
