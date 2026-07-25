"""Compute catalog resource tests."""

from __future__ import annotations

import pytest


def test_compute_catalog(mock_api, client):
    mock_api.get("/compute/catalog").respond(
        200,
        json={
            "data": {
                "products": [
                    {
                        "id": "computer",
                        "default_template": "miosa-desktop",
                        "templates": [
                            {
                                "id": "miosa-desktop",
                                "size_ids": ["small"],
                                "artifact_readiness": [
                                    {
                                        "size": "small",
                                        "state": "fast_ready",
                                        "checked_nodes": 10,
                                        "ready_nodes": 10,
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        },
    )

    catalog = client.regions.catalog()

    assert catalog["products"][0]["id"] == "computer"
    readiness = catalog["products"][0]["templates"][0]["artifact_readiness"][0]
    assert readiness["state"] == "fast_ready"
    assert readiness["ready_nodes"] == 10


@pytest.mark.asyncio
async def test_async_compute_catalog(mock_api, async_client):
    mock_api.get("/compute/catalog").respond(
        200,
        json={
            "data": {
                "products": [
                    {
                        "id": "sandbox",
                        "templates": [
                            {
                                "id": "nextjs",
                                "artifact_readiness": [
                                    {"size": "medium", "state": "cold_boot_only"}
                                ],
                            }
                        ],
                    }
                ]
            }
        },
    )

    catalog = await async_client.regions.catalog()

    assert catalog["products"][0]["templates"][0]["id"] == "nextjs"
