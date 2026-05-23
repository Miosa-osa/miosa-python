"""Storage resource — managed S3-compatible buckets + objects + presigned URLs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any, keys: tuple[str, ...] = ("data", "buckets", "objects", "items")) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data:
                return data[k]
    return data


class Storage:
    """Managed object storage — buckets and objects."""

    def __init__(self, transport: "SyncTransport") -> None:
        self._t = transport

    # ── Buckets ────────────────────────────────────────────────────────

    def list_buckets(self) -> List[Dict[str, Any]]:
        data = self._t.request("GET", "/storage/buckets")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def create_bucket(self, name: str, **attrs: Any) -> Dict[str, Any]:
        if "public" in attrs and "visibility" not in attrs:
            attrs["visibility"] = "public" if attrs.pop("public") else "private"

        body = {"name": name, **{k: v for k, v in attrs.items() if v is not None}}
        return _unwrap(self._t.request("POST", "/storage/buckets", json_body=body))

    def get_bucket(self, bucket_id: str) -> Dict[str, Any]:
        return _unwrap(self._t.request("GET", f"/storage/buckets/{bucket_id}"))

    def delete_bucket(self, bucket_id: str) -> None:
        self._t.request("DELETE", f"/storage/buckets/{bucket_id}")

    # ── Objects ────────────────────────────────────────────────────────

    def list_objects(
        self,
        bucket_id: str,
        *,
        prefix: Optional[str] = None,
        max_keys: Optional[int] = None,
        marker: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if prefix is not None:
            params["prefix"] = prefix
        effective_max_keys = max_keys if max_keys is not None else limit
        effective_marker = marker if marker is not None else cursor
        if effective_max_keys is not None:
            params["max_keys"] = effective_max_keys
        if effective_marker is not None:
            params["marker"] = effective_marker
        data = self._t.request(
            "GET",
            f"/storage/buckets/{bucket_id}/objects",
            params=params or None,
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    def put_object(
        self,
        bucket_id: str,
        key: str,
        content: bytes,
        *,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload bytes to ``bucket/:bucket_id/objects/:key``."""
        headers = {"Content-Type": content_type or "application/octet-stream"}
        return self._t.request(
            "PUT",
            f"/storage/buckets/{bucket_id}/objects/{key}",
            json_body=None,
            data=content,
            headers=headers,
        )

    def get_object(self, bucket_id: str, key: str) -> bytes:
        """Download the raw bytes of an object."""
        return self._t.request(
            "GET",
            f"/storage/buckets/{bucket_id}/objects/{key}",
            raw_response=True,
        ).content

    def delete_object(self, bucket_id: str, key: str) -> None:
        self._t.request("DELETE", f"/storage/buckets/{bucket_id}/objects/{key}")

    # ── Presigned URLs ─────────────────────────────────────────────────

    def presign(
        self,
        bucket_id: str,
        *,
        key: str,
        method: Optional[str] = None,
        expires_in: Optional[int] = None,
        operation: str = "get",
        expires_in_sec: int = 300,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mint a signed URL for direct browser upload/download.

        :param operation: ``"get"`` | ``"put"``
        """
        effective_method = method or ("PUT" if operation == "put" else "GET")
        body: Dict[str, Any] = {
            "key": key,
            "method": effective_method.upper(),
            "expires_in": expires_in if expires_in is not None else expires_in_sec,
        }
        return _unwrap(
            self._t.request(
                "POST", f"/storage/buckets/{bucket_id}/presign", json_body=body
            )
        )


class AsyncStorage:
    """Async object storage."""

    def __init__(self, transport: "AsyncTransport") -> None:
        self._t = transport

    async def list_buckets(self) -> List[Dict[str, Any]]:
        data = await self._t.request("GET", "/storage/buckets")
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def create_bucket(self, name: str, **attrs: Any) -> Dict[str, Any]:
        if "public" in attrs and "visibility" not in attrs:
            attrs["visibility"] = "public" if attrs.pop("public") else "private"

        body = {"name": name, **{k: v for k, v in attrs.items() if v is not None}}
        return _unwrap(
            await self._t.request("POST", "/storage/buckets", json_body=body)
        )

    async def get_bucket(self, bucket_id: str) -> Dict[str, Any]:
        return _unwrap(await self._t.request("GET", f"/storage/buckets/{bucket_id}"))

    async def delete_bucket(self, bucket_id: str) -> None:
        await self._t.request("DELETE", f"/storage/buckets/{bucket_id}")

    async def list_objects(
        self,
        bucket_id: str,
        *,
        prefix: Optional[str] = None,
        max_keys: Optional[int] = None,
        marker: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if prefix is not None:
            params["prefix"] = prefix
        effective_max_keys = max_keys if max_keys is not None else limit
        effective_marker = marker if marker is not None else cursor
        if effective_max_keys is not None:
            params["max_keys"] = effective_max_keys
        if effective_marker is not None:
            params["marker"] = effective_marker
        data = await self._t.request(
            "GET",
            f"/storage/buckets/{bucket_id}/objects",
            params=params or None,
        )
        result = _unwrap(data)
        return result if isinstance(result, list) else []

    async def put_object(
        self,
        bucket_id: str,
        key: str,
        content: bytes,
        *,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        headers = {"Content-Type": content_type or "application/octet-stream"}
        return await self._t.request(
            "PUT",
            f"/storage/buckets/{bucket_id}/objects/{key}",
            data=content,
            headers=headers,
        )

    async def get_object(self, bucket_id: str, key: str) -> bytes:
        resp = await self._t.request(
            "GET",
            f"/storage/buckets/{bucket_id}/objects/{key}",
            raw_response=True,
        )
        return resp.content

    async def delete_object(self, bucket_id: str, key: str) -> None:
        await self._t.request(
            "DELETE", f"/storage/buckets/{bucket_id}/objects/{key}"
        )

    async def presign(
        self,
        bucket_id: str,
        *,
        key: str,
        method: Optional[str] = None,
        expires_in: Optional[int] = None,
        operation: str = "get",
        expires_in_sec: int = 300,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        effective_method = method or ("PUT" if operation == "put" else "GET")
        body: Dict[str, Any] = {
            "key": key,
            "method": effective_method.upper(),
            "expires_in": expires_in if expires_in is not None else expires_in_sec,
        }
        return _unwrap(
            await self._t.request(
                "POST", f"/storage/buckets/{bucket_id}/presign", json_body=body
            )
        )
