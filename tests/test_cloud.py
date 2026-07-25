def test_cloud_aws_byoc_flow(mock_api, client):
    create = mock_api.post("/cloud/accounts").respond(
        201,
        json={
            "data": {
                "id": "cloud_acct_123",
                "provider": "aws",
                "mode": "customer_byoc",
                "external_id": "miosa_ext_abc",
            }
        },
    )
    attach = mock_api.post("/cloud/accounts/cloud_acct_123/aws/role").respond(
        200,
        json={
            "data": {
                "id": "cloud_acct_123",
                "role_arn": "arn:aws:iam::123456789012:role/MiosaByocRole",
                "default_region": "us-east-1",
            }
        },
    )
    region = mock_api.post("/cloud/regions").respond(
        201, json={"data": {"id": "region_1", "provider_region": "us-east-1"}}
    )
    pool = mock_api.post("/cloud/pools").respond(
        201, json={"data": {"id": "pool_1", "instance_type": "c6i.metal"}}
    )
    preflight = mock_api.post("/cloud/preflights").respond(
        201, json={"data": {"id": "run_1", "status": "pass"}}
    )
    list_preflights = mock_api.get("/cloud/preflights").respond(
        200, json={"data": [{"id": "run_1"}]}
    )

    account = client.cloud.create_account(
        provider="aws",
        mode="customer_byoc",
        displayName="Customer AWS",
        externalAccountId="123456789012",
    )
    attached = client.cloud.attach_aws_role(
        account["id"],
        role_arn="arn:aws:iam::123456789012:role/MiosaByocRole",
        defaultRegion="us-east-1",
    )
    created_region = client.cloud.create_region(
        cloudAccountId=account["id"],
        providerRegion="us-east-1",
        providerZone="us-east-1a",
        displayName="N. Virginia",
    )
    created_pool = client.cloud.create_pool(
        cloudRegionId=created_region["id"],
        instanceType="c6i.metal",
        targetNodes=1,
        maxNodes=4,
    )
    run = client.cloud.record_preflight(
        cloudAccountId=account["id"],
        provider="aws",
        status="pass",
        checks={"sts_identity": {"status": "pass"}},
    )
    runs = client.cloud.list_preflights(cloudAccountId=account["id"], limit=10)

    assert account["external_id"] == "miosa_ext_abc"
    assert attached["default_region"] == "us-east-1"
    assert created_pool["instance_type"] == "c6i.metal"
    assert run["status"] == "pass"
    assert runs[0]["id"] == "run_1"
    assert b'"external_account_id":"123456789012"' in create.calls.last.request.content
    assert (
        b'"role_arn":"arn:aws:iam::123456789012:role/MiosaByocRole"'
        in attach.calls.last.request.content
    )
    assert b'"provider_region":"us-east-1"' in region.calls.last.request.content
    assert b'"instance_type":"c6i.metal"' in pool.calls.last.request.content
    assert b'"cloud_account_id":"cloud_acct_123"' in preflight.calls.last.request.content
    assert "cloud_account_id=cloud_acct_123" in str(list_preflights.calls.last.request.url)
