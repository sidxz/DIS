"""Async HTTP client for checking permissions against the identity service."""

import uuid
from dataclasses import dataclass

import httpx


@dataclass
class PermissionCheck:
    service_name: str
    resource_type: str
    resource_id: uuid.UUID
    action: str  # 'view' | 'edit'


@dataclass
class PermissionResult:
    service_name: str
    resource_type: str
    resource_id: uuid.UUID
    action: str
    allowed: bool


class PermissionClient:
    """Client for the identity service's permission API."""

    def __init__(self, base_url: str, service_name: str):
        self.base_url = base_url.rstrip("/")
        self.service_name = service_name
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=5.0)

    async def check(
        self,
        token: str,
        checks: list[PermissionCheck],
    ) -> list[PermissionResult]:
        """Batch check permissions. Pass the user's JWT as the token."""
        response = await self._client.post(
            "/permissions/check",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "checks": [
                    {
                        "service_name": c.service_name,
                        "resource_type": c.resource_type,
                        "resource_id": str(c.resource_id),
                        "action": c.action,
                    }
                    for c in checks
                ]
            },
        )
        response.raise_for_status()
        data = response.json()
        return [
            PermissionResult(
                service_name=r["service_name"],
                resource_type=r["resource_type"],
                resource_id=uuid.UUID(r["resource_id"]),
                action=r["action"],
                allowed=r["allowed"],
            )
            for r in data["results"]
        ]

    async def can(
        self,
        token: str,
        resource_type: str,
        resource_id: uuid.UUID,
        action: str,
    ) -> bool:
        """Convenience: check a single permission."""
        results = await self.check(
            token,
            [PermissionCheck(self.service_name, resource_type, resource_id, action)],
        )
        return results[0].allowed if results else False

    async def register_resource(
        self,
        token: str,
        resource_type: str,
        resource_id: uuid.UUID,
        workspace_id: uuid.UUID,
        owner_id: uuid.UUID,
        visibility: str = "workspace",
    ) -> dict:
        """Register a new resource with the identity service."""
        response = await self._client.post(
            "/permissions/register",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "service_name": self.service_name,
                "resource_type": resource_type,
                "resource_id": str(resource_id),
                "workspace_id": str(workspace_id),
                "owner_id": str(owner_id),
                "visibility": visibility,
            },
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
