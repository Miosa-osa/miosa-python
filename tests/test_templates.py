from __future__ import annotations

import pytest

CATALOG = {
    "templates": [
        {
            "id": "miosa-sandbox",
            "product": "sandbox",
            "installed_tools": ["node", "python", "git"],
            "readiness_contract": {"exec_ready": True},
            "benchmark_lane": {"id": "default_customer_sandbox"},
            "sizes": [{"size": "small", "state": "fast_ready"}],
        },
        {
            "id": "miosa-desktop",
            "product": "computer",
            "readiness_contract": {"desktop_ready": True},
            "benchmark_lane": {"id": "computer_desktop"},
            "sizes": [{"size": "small", "state": "fast_ready"}],
        },
    ],
    "readiness_states": ["fast_ready", "cold_boot_only", "missing"],
}


def test_templates_lists_product_aware_catalog(mock_api, client):
    route = mock_api.get("/templates").respond(200, json=CATALOG)

    templates = client.templates.list()
    sandboxes = client.templates.list(product="sandbox")
    readiness = client.templates.readiness("miosa-desktop")

    assert route.called
    assert len(templates) == 2
    assert [t["id"] for t in sandboxes] == ["miosa-sandbox"]
    assert readiness == [{"size": "small", "state": "fast_ready"}]


def test_templates_get_raises_for_missing_template(mock_api, client):
    mock_api.get("/templates").respond(200, json=CATALOG)

    with pytest.raises(KeyError, match="not-real"):
        client.templates.get("not-real")


def test_templates_keeps_sandbox_template_crud_compatibility(mock_api, client):
    route = mock_api.post("/sandbox-templates").respond(
        201,
        json={
            "data": {
                "id": "tmpl_123",
                "name": "Custom",
                "slug": "custom",
                "template_type": "miosa-sandbox",
            }
        },
    )

    created = client.templates.create(
        name="Custom",
        build_spec={"steps": []},
        slug="custom",
        template_type="miosa-sandbox",
    )

    assert route.called
    assert created["id"] == "tmpl_123"


async def test_async_templates_lists_product_aware_catalog(mock_api, async_client):
    route = mock_api.get("/templates").respond(200, json=CATALOG)

    templates = await async_client.templates.list(product="computer")
    readiness = await async_client.templates.readiness("miosa-desktop")

    await async_client.close()

    assert route.called
    assert [t["id"] for t in templates] == ["miosa-desktop"]
    assert readiness == [{"size": "small", "state": "fast_ready"}]
