"""Tests for PermissionClient using respx to mock httpx."""

import uuid

import httpx
import pytest
import respx

from sentinel_auth.permissions import PermissionCheck, PermissionClient


@pytest.fixture()
def client():
    return PermissionClient("https://auth.test", "docu-store", service_key="sk-test")


RES_ID = uuid.uuid4()
WS_ID = uuid.uuid4()
OWNER_ID = uuid.uuid4()


class TestPermissionClient:
    @respx.mock
    async def test_can_allowed(self, client):
        respx.post("https://auth.test/permissions/check").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "service_name": "docu-store",
                            "resource_type": "document",
                            "resource_id": str(RES_ID),
                            "action": "view",
                            "allowed": True,
                        }
                    ]
                },
            )
        )
        result = await client.can("tok", "document", RES_ID, "view")
        assert result is True

    @respx.mock
    async def test_can_denied(self, client):
        respx.post("https://auth.test/permissions/check").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "service_name": "docu-store",
                            "resource_type": "document",
                            "resource_id": str(RES_ID),
                            "action": "edit",
                            "allowed": False,
                        }
                    ]
                },
            )
        )
        result = await client.can("tok", "document", RES_ID, "edit")
        assert result is False

    @respx.mock
    async def test_check_batch(self, client):
        r1, r2 = uuid.uuid4(), uuid.uuid4()
        respx.post("https://auth.test/permissions/check").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "service_name": "docu-store",
                            "resource_type": "doc",
                            "resource_id": str(r1),
                            "action": "view",
                            "allowed": True,
                        },
                        {
                            "service_name": "docu-store",
                            "resource_type": "doc",
                            "resource_id": str(r2),
                            "action": "edit",
                            "allowed": False,
                        },
                    ]
                },
            )
        )
        checks = [
            PermissionCheck("docu-store", "doc", r1, "view"),
            PermissionCheck("docu-store", "doc", r2, "edit"),
        ]
        results = await client.check("tok", checks)
        assert len(results) == 2
        assert results[0].allowed is True
        assert results[1].allowed is False

    @respx.mock
    async def test_register_resource(self, client):
        respx.post("https://auth.test/permissions/register").mock(return_value=httpx.Response(200, json={"id": "abc"}))
        result = await client.register_resource("document", RES_ID, WS_ID, OWNER_ID)
        assert result == {"id": "abc"}

    @respx.mock
    async def test_accessible(self, client):
        r1, r2 = uuid.uuid4(), uuid.uuid4()
        respx.post("https://auth.test/permissions/accessible").mock(
            return_value=httpx.Response(
                200,
                json={"resource_ids": [str(r1), str(r2)], "has_full_access": False},
            )
        )
        ids, full = await client.accessible("tok", "document", "view", WS_ID)
        assert len(ids) == 2
        assert full is False

    @respx.mock
    async def test_accessible_full_access(self, client):
        respx.post("https://auth.test/permissions/accessible").mock(
            return_value=httpx.Response(
                200,
                json={"resource_ids": [], "has_full_access": True},
            )
        )
        ids, full = await client.accessible("tok", "document", "view", WS_ID)
        assert ids == []
        assert full is True

    async def test_context_manager(self):
        async with PermissionClient("https://auth.test", "svc") as client:
            assert client.service_name == "svc"

    def test_headers_with_service_key_and_token(self, client):
        h = client._headers("my-jwt")
        assert h["X-Service-Key"] == "sk-test"
        assert h["Authorization"] == "Bearer my-jwt"

    def test_headers_without_token(self, client):
        h = client._headers()
        assert "Authorization" not in h
        assert h["X-Service-Key"] == "sk-test"
