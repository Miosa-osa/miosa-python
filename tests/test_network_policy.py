"""Tests for the NetworkPolicy resource."""

from __future__ import annotations

import json

from miosa.types import NetworkPolicyData, NetworkPolicyEffect

from .conftest import COMPUTER_JSON

POLICY_JSON = {
    "computer_id": "comp_abc123",
    "tenant_id": "tnt_1",
    "rules": [
        {"effect": "deny", "destination": "169.254.169.254/32"},
        {"effect": "allow", "destination": "example.com", "ports": "443", "protocol": "tcp"},
    ],
    "default_effect": "allow",
    "inserted_at": "2026-04-01T00:00:00Z",
    "updated_at": "2026-04-01T00:00:00Z",
}


def _get_computer(mock_api, client):
    mock_api.get("/computers/comp_abc123").respond(200, json=COMPUTER_JSON)
    return client.computers.get("comp_abc123")


class TestNetworkPolicy:
    def test_get_returns_policy(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        mock_api.get("/computers/comp_abc123/network-policy").respond(
            200, json={"data": POLICY_JSON}
        )
        policy = comp.network_policy.get()
        assert isinstance(policy, NetworkPolicyData)
        assert policy.default_effect == NetworkPolicyEffect.ALLOW
        assert len(policy.rules) == 2

    def test_set_sends_put_with_rules(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        route = mock_api.put("/computers/comp_abc123/network-policy").respond(
            200, json={"data": POLICY_JSON}
        )
        policy = comp.network_policy.set(
            rules=[
                {"effect": "deny", "destination": "169.254.169.254/32"},
                {
                    "effect": "allow",
                    "destination": "example.com",
                    "ports": "443",
                    "protocol": "tcp",
                },
            ],
            default_effect="allow",
        )
        assert policy.default_effect == NetworkPolicyEffect.ALLOW

        body = json.loads(route.calls.last.request.content)
        assert body["default_effect"] == "allow"
        assert len(body["rules"]) == 2
        assert body["rules"][0]["destination"] == "169.254.169.254/32"

    def test_set_accepts_enum_effect(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        route = mock_api.put("/computers/comp_abc123/network-policy").respond(
            200, json={"data": POLICY_JSON}
        )
        comp.network_policy.set(
            rules=[{"effect": "deny", "destination": "any"}],
            default_effect=NetworkPolicyEffect.DENY,
        )
        body = json.loads(route.calls.last.request.content)
        assert body["default_effect"] == "deny"

    def test_set_omits_default_effect_when_none(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        route = mock_api.put("/computers/comp_abc123/network-policy").respond(
            200, json={"data": POLICY_JSON}
        )
        comp.network_policy.set(
            rules=[{"effect": "deny", "destination": "any"}],
        )
        body = json.loads(route.calls.last.request.content)
        assert "default_effect" not in body

    def test_reset_sends_delete(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        route = mock_api.delete("/computers/comp_abc123/network-policy").respond(
            200, json={}
        )
        comp.network_policy.reset()
        assert route.called
