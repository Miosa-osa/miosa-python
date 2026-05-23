"""Egress network policy management for a Computer.

Accessed via ``computer.network_policy``. A policy is a list of rules
evaluated top-to-bottom, with a ``default_effect`` applied when none
match. Writes propagate to the host ``nftables`` immediately — no
VM restart required.

Example — block IMDS + metadata endpoints::

    computer.network_policy.set(
        default_effect="allow",
        rules=[
            {"effect": "deny", "destination": "169.254.169.254/32"},
            {"effect": "deny", "destination": "metadata.google.internal"},
        ],
    )

Example — allowlist mode (deny by default)::

    computer.network_policy.set(
        default_effect="deny",
        rules=[
            {"effect": "allow", "destination": "example.com",
             "ports": "443", "protocol": "tcp"},
        ],
    )
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, List, Optional, Union

from ..types import (
    NetworkPolicyData,
    NetworkPolicyEffect,
    NetworkPolicyRule,
)

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


RuleInput = Union[NetworkPolicyRule, dict]
EffectInput = Union[NetworkPolicyEffect, str]


def _unwrap(data: Any, key: str = "data") -> Any:
    if isinstance(data, dict) and key in data and len(data) <= 2:
        return data[key]
    return data


def _normalise_rules(rules: Iterable[RuleInput]) -> List[dict]:
    out: List[dict] = []
    for rule in rules:
        if isinstance(rule, NetworkPolicyRule):
            out.append(rule.model_dump(exclude_none=True, by_alias=True))
        else:
            out.append({k: v for k, v in rule.items() if v is not None})
    return out


def _effect_value(effect: Optional[EffectInput]) -> Optional[str]:
    if effect is None:
        return None
    if isinstance(effect, NetworkPolicyEffect):
        return effect.value
    return effect


class NetworkPolicy:
    """Synchronous network-policy management."""

    def __init__(self, transport: SyncTransport, computer_id: str) -> None:
        self._transport = transport
        self._computer_id = computer_id

    def _path(self) -> str:
        return f"/computers/{self._computer_id}/network-policy"

    def get(self) -> NetworkPolicyData:
        """Return the current policy (or the default allow-all if none set)."""
        raw = self._transport.request("GET", self._path())
        return NetworkPolicyData.model_validate(_unwrap(raw))

    def set(
        self,
        *,
        rules: Iterable[RuleInput],
        default_effect: Optional[EffectInput] = None,
    ) -> NetworkPolicyData:
        """Create or replace the policy. Returns the persisted record."""
        body: dict = {"rules": _normalise_rules(rules)}
        ev = _effect_value(default_effect)
        if ev is not None:
            body["default_effect"] = ev
        raw = self._transport.request("PUT", self._path(), json_body=body)
        return NetworkPolicyData.model_validate(_unwrap(raw))

    def reset(self) -> None:
        """Reset to the default allow-all policy. Idempotent."""
        self._transport.request("DELETE", self._path())


class AsyncNetworkPolicy:
    """Asynchronous network-policy management."""

    def __init__(self, transport: AsyncTransport, computer_id: str) -> None:
        self._transport = transport
        self._computer_id = computer_id

    def _path(self) -> str:
        return f"/computers/{self._computer_id}/network-policy"

    async def get(self) -> NetworkPolicyData:
        raw = await self._transport.request("GET", self._path())
        return NetworkPolicyData.model_validate(_unwrap(raw))

    async def set(
        self,
        *,
        rules: Iterable[RuleInput],
        default_effect: Optional[EffectInput] = None,
    ) -> NetworkPolicyData:
        body: dict = {"rules": _normalise_rules(rules)}
        ev = _effect_value(default_effect)
        if ev is not None:
            body["default_effect"] = ev
        raw = await self._transport.request("PUT", self._path(), json_body=body)
        return NetworkPolicyData.model_validate(_unwrap(raw))

    async def reset(self) -> None:
        await self._transport.request("DELETE", self._path())
