from __future__ import annotations


def test_runtime_capabilities_gets_live_contract(mock_api, client):
    route = mock_api.get("/runtime-capabilities").respond(
        200,
        json={
            "data": {
                "version": 1,
                "runs": {
                    "contract_fields": ["execution_packet", "expected_outputs"],
                },
            }
        },
    )

    result = client.runtime_capabilities.get()

    assert route.called
    assert result["runs"]["contract_fields"] == [
        "execution_packet",
        "expected_outputs",
    ]
