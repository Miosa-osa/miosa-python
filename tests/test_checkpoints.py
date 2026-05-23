"""Tests for the Checkpoints resource."""

from __future__ import annotations

from miosa.types import SnapshotData, SnapshotStatus

from .conftest import COMPUTER_JSON

SNAPSHOT_JSON = {
    "id": "snap_001",
    "computer_id": "comp_abc123",
    "tenant_id": "tnt_1",
    "comment": "pre-upgrade",
    "status": "ready",
    "state_size_bytes": 1024,
    "memory_size_bytes": 2048,
    "rootfs_size_bytes": 4096,
    "compressed_size_bytes": 512,
    "s3_bucket": "miosa-snapshots",
    "s3_prefix": "comp_abc123/snap_001",
    "parent_snapshot_id": None,
    "error": None,
    "created_at": "2026-04-01T00:00:00Z",
    "updated_at": "2026-04-01T00:00:00Z",
}


def _get_computer(mock_api, client):
    mock_api.get("/computers/comp_abc123").respond(200, json=COMPUTER_JSON)
    return client.computers.get("comp_abc123")


class TestCheckpoints:
    def test_create_sends_comment(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        route = mock_api.post("/computers/comp_abc123/snapshots").respond(
            200, json={"data": SNAPSHOT_JSON}
        )
        snap = comp.checkpoints.create(comment="pre-upgrade")
        assert isinstance(snap, SnapshotData)
        assert snap.id == "snap_001"
        assert snap.status == SnapshotStatus.READY
        assert route.called
        assert b'"comment":"pre-upgrade"' in route.calls.last.request.content

    def test_list(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        mock_api.get("/computers/comp_abc123/snapshots").respond(
            200, json={"data": [SNAPSHOT_JSON]}
        )
        snaps = comp.checkpoints.list()
        assert len(snaps) == 1
        assert snaps[0].id == "snap_001"

    def test_get(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        mock_api.get("/computers/comp_abc123/snapshots/snap_001").respond(
            200, json={"data": SNAPSHOT_JSON}
        )
        snap = comp.checkpoints.get("snap_001")
        assert snap.id == "snap_001"

    def test_delete_returns_deleted_snapshot(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        deleted = {**SNAPSHOT_JSON, "status": "deleted"}
        mock_api.delete("/computers/comp_abc123/snapshots/snap_001").respond(
            200, json={"data": deleted}
        )
        snap = comp.checkpoints.delete("snap_001")
        assert snap.status == SnapshotStatus.DELETED

    def test_restore_returns_bound_computer(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        mock_api.post("/computers/comp_abc123/restore/snap_001").respond(
            200, json={"data": COMPUTER_JSON, "snapshot": SNAPSHOT_JSON}
        )
        restored = comp.checkpoints.restore("snap_001")
        assert restored.id == "comp_abc123"
        assert restored.name == "test-agent"
