"""Smoke tests for the OpenComputers namespace (sync + async)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from miosa import AsyncMiosa, Miosa
from miosa.errors import AuthenticationError, NotFoundError

API_KEY = "msk_u_test_key_12345"
BASE_URL = "https://api.miosa.ai/api/v1"

HOST_JSON = {
    "id": "host_abc",
    "name": "my-mac",
    "region": None,
    "status": "online",
    "tenant_id": "t_1",
    "labels": {},
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}

JOB_JSON = {
    "id": "job_1",
    "host_id": "host_abc",
    "status": "completed",
    "command": "npm test",
    "args": [],
    "env": [],
    "cwd": None,
    "exit_code": 0,
    "stdout": "ok",
    "stderr": "",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
    "completed_at": "2026-01-01T00:00:01Z",
}

TUNNEL_JSON = {
    "id": "tun_1",
    "host_id": "host_abc",
    "slug": "abc123",
    "target_port": 3000,
    "auth_mode": "public",
    "public_url": "https://api.miosa.ai/t/abc123",
    "enabled": True,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}

SESSION_JSON = {
    "id": "sess_1",
    "host_id": "host_abc",
    "task": "run tests",
    "model_id": None,
    "status": "pending",
    "max_turns": 20,
    "turns_used": 0,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
    "completed_at": None,
    "error": None,
}


# ---------------------------------------------------------------------------
# Hosts — sync
# ---------------------------------------------------------------------------


def test_hosts_list(client: Miosa):
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        router.get("/opencomputers/hosts").mock(
            return_value=httpx.Response(
                200, json={"data": [HOST_JSON], "meta": {"total": 1, "page": 1, "per_page": 20}}
            )
        )
        result = client.open_computers.hosts.list()
    assert len(result.data) == 1
    assert result.data[0].id == "host_abc"


def test_hosts_create_returns_host_key(client: Miosa):
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        router.post("/opencomputers/hosts").mock(
            return_value=httpx.Response(200, json={**HOST_JSON, "host_key": "hk_secret"})
        )
        host = client.open_computers.hosts.create(
            __import__(
                "miosa.resources.open_computers.types", fromlist=["HostCreateParams"]
            ).HostCreateParams(name="my-mac")
        )
    assert host.host_key == "hk_secret"


def test_hosts_get(client: Miosa):
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        router.get("/opencomputers/hosts/host_abc").mock(
            return_value=httpx.Response(200, json=HOST_JSON)
        )
        host = client.open_computers.hosts.get("host_abc")
    assert host.status.value == "online"


def test_hosts_revoke(client: Miosa):
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        router.delete("/opencomputers/hosts/host_abc").mock(
            return_value=httpx.Response(204)
        )
        # Should not raise
        client.open_computers.hosts.revoke("host_abc")


# ---------------------------------------------------------------------------
# Jobs — sync
# ---------------------------------------------------------------------------


def test_jobs_run(client: Miosa):
    from miosa.resources.open_computers.types import JobRunParams

    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        router.post("/opencomputers/hosts/host_abc/exec").mock(
            return_value=httpx.Response(200, json=JOB_JSON)
        )
        job = client.open_computers.jobs.run("host_abc", JobRunParams(command="npm test"))
    assert job.id == "job_1"
    assert job.exit_code == 0


def test_jobs_list(client: Miosa):
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        router.get("/opencomputers/hosts/host_abc/exec").mock(
            return_value=httpx.Response(
                200, json={"data": [JOB_JSON], "meta": {"total": 1, "page": 1, "per_page": 20}}
            )
        )
        result = client.open_computers.jobs.list("host_abc")
    assert result.data[0].command == "npm test"


def test_jobs_cancel(client: Miosa):
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        router.delete("/opencomputers/hosts/host_abc/exec/job_1").mock(
            return_value=httpx.Response(204)
        )
        client.open_computers.jobs.cancel("host_abc", "job_1")


# ---------------------------------------------------------------------------
# Tunnels — sync
# ---------------------------------------------------------------------------


def test_tunnels_create(client: Miosa):
    from miosa.resources.open_computers.types import TunnelCreateParams

    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        router.post("/opencomputers/hosts/host_abc/tunnels").mock(
            return_value=httpx.Response(200, json=TUNNEL_JSON)
        )
        tunnel = client.open_computers.tunnels.create(
            "host_abc", TunnelCreateParams(target_port=3000)
        )
    assert tunnel.public_url == "https://api.miosa.ai/t/abc123"


def test_tunnels_delete(client: Miosa):
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        router.delete("/opencomputers/hosts/host_abc/tunnels/tun_1").mock(
            return_value=httpx.Response(204)
        )
        client.open_computers.tunnels.delete("host_abc", "tun_1")


# ---------------------------------------------------------------------------
# Agents — sync
# ---------------------------------------------------------------------------


def test_agents_dispatch(client: Miosa):
    from miosa.resources.open_computers.types import AgentDispatchParams

    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        router.post("/opencomputers/hosts/host_abc/agent/dispatch").mock(
            return_value=httpx.Response(200, json=SESSION_JSON)
        )
        session = client.open_computers.agents.dispatch(
            "host_abc", AgentDispatchParams(task="run tests")
        )
    assert session.id == "sess_1"


def test_agents_dispatch_accepts_current_backend_shape(client: Miosa):
    from miosa.resources.open_computers.types import AgentDispatchParams

    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        router.post("/opencomputers/hosts/host_abc/agent/dispatch").mock(
            return_value=httpx.Response(
                200,
                json={
                    "session_id": "sess_2",
                    "host_id": "host_abc",
                    "task": "run tests",
                    "status": "running",
                    "agent_runtime_profile_id": "prof_123",
                    "runtime_context": {
                        "agent_runtime_profile": {
                            "id": "prof_123",
                            "runtime": "claude-code",
                        }
                    },
                },
            )
        )
        session = client.open_computers.agents.dispatch(
            "host_abc",
            AgentDispatchParams(task="run tests", agent_runtime_profile_id="prof_123"),
        )

    assert session.id == "sess_2"
    assert session.agent_runtime_profile_id == "prof_123"


def test_agents_cancel(client: Miosa):
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        router.delete("/opencomputers/hosts/host_abc/agent/sessions/sess_1").mock(
            return_value=httpx.Response(204)
        )
        client.open_computers.agents.cancel("host_abc", "sess_1")


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_hosts_list_401(client: Miosa):
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        router.get("/opencomputers/hosts").mock(
            return_value=httpx.Response(
                401, json={"error": {"code": "UNAUTHORIZED", "message": "Unauthorized"}}
            )
        )
        with pytest.raises(AuthenticationError):
            client.open_computers.hosts.list()


def test_hosts_get_404(client: Miosa):
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        router.get("/opencomputers/hosts/bad").mock(
            return_value=httpx.Response(
                404, json={"error": {"code": "NOT_FOUND", "message": "Host not found"}}
            )
        )
        with pytest.raises(NotFoundError):
            client.open_computers.hosts.get("bad")


# ---------------------------------------------------------------------------
# Async variants — smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_hosts_list():
    client = AsyncMiosa(api_key=API_KEY, base_url=BASE_URL, max_retries=0)
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        router.get("/opencomputers/hosts").mock(
            return_value=httpx.Response(
                200, json={"data": [HOST_JSON], "meta": {"total": 1, "page": 1, "per_page": 20}}
            )
        )
        result = await client.open_computers.hosts.list()
    await client.close()
    assert result.data[0].name == "my-mac"


@pytest.mark.asyncio
async def test_async_jobs_run():
    from miosa.resources.open_computers.types import JobRunParams

    client = AsyncMiosa(api_key=API_KEY, base_url=BASE_URL, max_retries=0)
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        router.post("/opencomputers/hosts/host_abc/exec").mock(
            return_value=httpx.Response(200, json=JOB_JSON)
        )
        job = await client.open_computers.jobs.run("host_abc", JobRunParams(command="npm test"))
    await client.close()
    assert job.status.value == "completed"
