"""Tests for the CustomDomains resource."""

from __future__ import annotations

import json

from miosa.types import CustomDomainData, CustomDomainStatus

from .conftest import COMPUTER_JSON

DOMAIN_JSON = {
    "id": "dom_001",
    "computer_id": "comp_abc123",
    "tenant_id": "tnt_1",
    "fqdn": "app.example.com",
    "status": "pending",
    "verification_target": "comp_abc123.sandbox.miosa.ai",
    "instructions": "Add CNAME app.example.com → comp_abc123.sandbox.miosa.ai",
    "verified_at": None,
    "tls_issued_at": None,
    "created_at": "2026-04-01T00:00:00Z",
    "updated_at": "2026-04-01T00:00:00Z",
}


def _get_computer(mock_api, client):
    mock_api.get("/computers/comp_abc123").respond(200, json=COMPUTER_JSON)
    return client.computers.get("comp_abc123")


class TestCustomDomains:
    def test_register_sends_fqdn(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        route = mock_api.post("/computers/comp_abc123/domains").respond(
            200, json={"data": DOMAIN_JSON}
        )
        domain = comp.domains.register("app.example.com")
        assert isinstance(domain, CustomDomainData)
        assert domain.fqdn == "app.example.com"
        assert domain.status == CustomDomainStatus.PENDING

        body = json.loads(route.calls.last.request.content)
        assert body == {"fqdn": "app.example.com"}

    def test_list(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        mock_api.get("/computers/comp_abc123/domains").respond(
            200, json={"data": [DOMAIN_JSON]}
        )
        domains = comp.domains.list()
        assert len(domains) == 1
        assert domains[0].fqdn == "app.example.com"

    def test_verify(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        verified = {**DOMAIN_JSON, "status": "verified"}
        mock_api.post("/computers/comp_abc123/domains/dom_001/verify").respond(
            200, json={"data": verified}
        )
        result = comp.domains.verify("dom_001")
        assert result.status == CustomDomainStatus.VERIFIED

    def test_delete(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        route = mock_api.delete("/computers/comp_abc123/domains/dom_001").respond(
            200, json={}
        )
        comp.domains.delete("dom_001")
        assert route.called

    def test_register_returns_instructions(self, mock_api, client):
        comp = _get_computer(mock_api, client)
        mock_api.post("/computers/comp_abc123/domains").respond(
            200, json={"data": DOMAIN_JSON}
        )
        domain = comp.domains.register("app.example.com")
        assert "CNAME" in (domain.instructions or "")
        assert domain.verification_target is not None
