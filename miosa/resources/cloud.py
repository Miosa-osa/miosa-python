"""Cloud accounts / BYOC / cloudburst control-plane state."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .._http import AsyncTransport, SyncTransport


def _unwrap(data: Any) -> Any:
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data


def _unwrap_list(data: Any) -> list[dict[str, Any]]:
    value = _unwrap(data)
    return value if isinstance(value, list) else []


def _compact(body: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in body.items() if value is not None}


class Cloud:
    """Cloud account, region, pool, and preflight APIs."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def list_accounts(self) -> list[dict[str, Any]]:
        return _unwrap_list(self._t.request("GET", "/cloud/accounts"))

    def create_account(self, *, provider: str, mode: str, **params: Any) -> dict[str, Any]:
        """Create a MIOSA-managed or customer BYOC cloud account."""
        return _unwrap(
            self._t.request(
                "POST",
                "/cloud/accounts",
                json_body=_compact(
                    {
                        "provider": provider,
                        "mode": mode,
                        "display_name": params.get("display_name")
                        or params.get("displayName"),
                        "external_account_id": params.get("external_account_id")
                        or params.get("externalAccountId"),
                        "credential_type": params.get("credential_type")
                        or params.get("credentialType"),
                        "default_region": params.get("default_region")
                        or params.get("defaultRegion"),
                        "metadata": params.get("metadata"),
                    }
                ),
            )
        )

    def attach_aws_role(self, account_id: str, *, role_arn: str, **params: Any) -> dict[str, Any]:
        """Attach the customer-created AWS assume-role ARN to a BYOC account."""
        return _unwrap(
            self._t.request(
                "POST",
                f"/cloud/accounts/{account_id}/aws/role",
                json_body=_compact(
                    {
                        "role_arn": role_arn,
                        "default_region": params.get("default_region")
                        or params.get("defaultRegion"),
                    }
                ),
            )
        )

    def list_regions(self, **filters: Any) -> list[dict[str, Any]]:
        return _unwrap_list(
            self._t.request(
                "GET",
                "/cloud/regions",
                params=_compact(
                    {
                        "cloud_account_id": filters.get("cloud_account_id")
                        or filters.get("cloudAccountId")
                    }
                )
                or None,
            )
        )

    def create_region(self, **params: Any) -> dict[str, Any]:
        return _unwrap(
            self._t.request(
                "POST",
                "/cloud/regions",
                json_body=_compact(
                    {
                        "cloud_account_id": params.get("cloud_account_id")
                        or params.get("cloudAccountId"),
                        "provider_region": params.get("provider_region")
                        or params.get("providerRegion"),
                        "provider_zone": params.get("provider_zone")
                        or params.get("providerZone"),
                        "display_name": params.get("display_name")
                        or params.get("displayName"),
                        "guest_supernet": params.get("guest_supernet")
                        or params.get("guestSupernet"),
                        "artifact_manifest_uri": params.get("artifact_manifest_uri")
                        or params.get("artifactManifestUri"),
                        "network_ref": params.get("network_ref") or params.get("networkRef"),
                        "subnet_ref": params.get("subnet_ref") or params.get("subnetRef"),
                        "security_group_refs": params.get("security_group_refs")
                        or params.get("securityGroupRefs"),
                        "instance_profile_ref": params.get("instance_profile_ref")
                        or params.get("instanceProfileRef"),
                        "metadata": params.get("metadata"),
                    }
                ),
            )
        )

    def list_pools(self, **filters: Any) -> list[dict[str, Any]]:
        return _unwrap_list(
            self._t.request(
                "GET",
                "/cloud/pools",
                params=_compact(
                    {
                        "cloud_region_id": filters.get("cloud_region_id")
                        or filters.get("cloudRegionId")
                    }
                )
                or None,
            )
        )

    def create_pool(self, **params: Any) -> dict[str, Any]:
        return _unwrap(
            self._t.request(
                "POST",
                "/cloud/pools",
                json_body=_compact(
                    {
                        "cloud_region_id": params.get("cloud_region_id")
                        or params.get("cloudRegionId"),
                        "pool_kind": params.get("pool_kind") or params.get("poolKind"),
                        "node_type": params.get("node_type") or params.get("nodeType"),
                        "instance_type": params.get("instance_type")
                        or params.get("instanceType"),
                        "target_nodes": params.get("target_nodes")
                        or params.get("targetNodes"),
                        "max_nodes": params.get("max_nodes") or params.get("maxNodes"),
                        "ttl_seconds": params.get("ttl_seconds")
                        or params.get("ttlSeconds"),
                        "max_hourly_cents": params.get("max_hourly_cents")
                        or params.get("maxHourlyCents"),
                        "placement_scope": params.get("placement_scope")
                        or params.get("placementScope"),
                        "metadata": params.get("metadata"),
                    }
                ),
            )
        )

    def list_preflights(self, **filters: Any) -> list[dict[str, Any]]:
        return _unwrap_list(
            self._t.request(
                "GET",
                "/cloud/preflights",
                params=_compact(
                    {
                        "cloud_account_id": filters.get("cloud_account_id")
                        or filters.get("cloudAccountId"),
                        "cloud_region_id": filters.get("cloud_region_id")
                        or filters.get("cloudRegionId"),
                        "limit": filters.get("limit"),
                    }
                )
                or None,
            )
        )

    def record_preflight(self, *, provider: str, status: str, **params: Any) -> dict[str, Any]:
        return _unwrap(
            self._t.request(
                "POST",
                "/cloud/preflights",
                json_body=_compact(
                    {
                        "cloud_account_id": params.get("cloud_account_id")
                        or params.get("cloudAccountId"),
                        "cloud_region_id": params.get("cloud_region_id")
                        or params.get("cloudRegionId"),
                        "provider": provider,
                        "status": status,
                        "checks": params.get("checks"),
                        "raw_report": params.get("raw_report") or params.get("rawReport"),
                        "metadata": params.get("metadata"),
                    }
                ),
            )
        )


class AsyncCloud:
    """Async cloud account, region, pool, and preflight APIs."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def list_accounts(self) -> list[dict[str, Any]]:
        return _unwrap_list(await self._t.request("GET", "/cloud/accounts"))

    async def create_account(self, *, provider: str, mode: str, **params: Any) -> dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                "/cloud/accounts",
                json_body=_compact(
                    {
                        "provider": provider,
                        "mode": mode,
                        "display_name": params.get("display_name")
                        or params.get("displayName"),
                        "external_account_id": params.get("external_account_id")
                        or params.get("externalAccountId"),
                        "credential_type": params.get("credential_type")
                        or params.get("credentialType"),
                        "default_region": params.get("default_region")
                        or params.get("defaultRegion"),
                        "metadata": params.get("metadata"),
                    }
                ),
            )
        )

    async def attach_aws_role(
        self, account_id: str, *, role_arn: str, **params: Any
    ) -> dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                f"/cloud/accounts/{account_id}/aws/role",
                json_body=_compact(
                    {
                        "role_arn": role_arn,
                        "default_region": params.get("default_region")
                        or params.get("defaultRegion"),
                    }
                ),
            )
        )

    async def list_regions(self, **filters: Any) -> list[dict[str, Any]]:
        return _unwrap_list(
            await self._t.request(
                "GET",
                "/cloud/regions",
                params=_compact(
                    {
                        "cloud_account_id": filters.get("cloud_account_id")
                        or filters.get("cloudAccountId")
                    }
                )
                or None,
            )
        )

    async def create_region(self, **params: Any) -> dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                "/cloud/regions",
                json_body=_compact(
                    {
                        "cloud_account_id": params.get("cloud_account_id")
                        or params.get("cloudAccountId"),
                        "provider_region": params.get("provider_region")
                        or params.get("providerRegion"),
                        "provider_zone": params.get("provider_zone")
                        or params.get("providerZone"),
                        "display_name": params.get("display_name")
                        or params.get("displayName"),
                        "metadata": params.get("metadata"),
                    }
                ),
            )
        )

    async def list_pools(self, **filters: Any) -> list[dict[str, Any]]:
        return _unwrap_list(
            await self._t.request(
                "GET",
                "/cloud/pools",
                params=_compact(
                    {
                        "cloud_region_id": filters.get("cloud_region_id")
                        or filters.get("cloudRegionId")
                    }
                )
                or None,
            )
        )

    async def create_pool(self, **params: Any) -> dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                "/cloud/pools",
                json_body=_compact(
                    {
                        "cloud_region_id": params.get("cloud_region_id")
                        or params.get("cloudRegionId"),
                        "instance_type": params.get("instance_type")
                        or params.get("instanceType"),
                        "target_nodes": params.get("target_nodes")
                        or params.get("targetNodes"),
                        "max_nodes": params.get("max_nodes") or params.get("maxNodes"),
                        "pool_kind": params.get("pool_kind") or params.get("poolKind"),
                        "metadata": params.get("metadata"),
                    }
                ),
            )
        )

    async def list_preflights(self, **filters: Any) -> list[dict[str, Any]]:
        return _unwrap_list(
            await self._t.request(
                "GET",
                "/cloud/preflights",
                params=_compact(
                    {
                        "cloud_account_id": filters.get("cloud_account_id")
                        or filters.get("cloudAccountId"),
                        "cloud_region_id": filters.get("cloud_region_id")
                        or filters.get("cloudRegionId"),
                        "limit": filters.get("limit"),
                    }
                )
                or None,
            )
        )

    async def record_preflight(
        self, *, provider: str, status: str, **params: Any
    ) -> dict[str, Any]:
        return _unwrap(
            await self._t.request(
                "POST",
                "/cloud/preflights",
                json_body=_compact(
                    {
                        "cloud_account_id": params.get("cloud_account_id")
                        or params.get("cloudAccountId"),
                        "cloud_region_id": params.get("cloud_region_id")
                        or params.get("cloudRegionId"),
                        "provider": provider,
                        "status": status,
                        "checks": params.get("checks"),
                        "raw_report": params.get("raw_report") or params.get("rawReport"),
                        "metadata": params.get("metadata"),
                    }
                ),
            )
        )
