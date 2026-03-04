import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.permission import (
    PermissionCheckRequest,
    PermissionCheckResponse,
    PermissionCheckResult,
    RegisterResourceRequest,
    ResourcePermissionResponse,
    ShareRequest,
    UpdateVisibilityRequest,
)
from src.services import permission_service

router = APIRouter(prefix="/permissions", tags=["permissions"])


# TODO: replace with JWT-based dependency
async def _get_current_user_id() -> uuid.UUID:
    raise HTTPException(status_code=401, detail="Not authenticated")


@router.post("/check", response_model=PermissionCheckResponse)
async def check_permissions(
    body: PermissionCheckRequest,
    db: AsyncSession = Depends(get_db),
):
    # TODO: extract user context from JWT (user_id, workspace_id, workspace_role, group_ids)
    raise HTTPException(status_code=501, detail="Not implemented yet — requires JWT context")


@router.post("/register", response_model=ResourcePermissionResponse, status_code=201)
async def register_resource(
    body: RegisterResourceRequest,
    db: AsyncSession = Depends(get_db),
):
    perm = await permission_service.register_resource(
        db,
        service_name=body.service_name,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        workspace_id=body.workspace_id,
        owner_id=body.owner_id,
        visibility=body.visibility,
    )
    return perm


@router.patch("/{permission_id}/visibility", response_model=ResourcePermissionResponse)
async def update_visibility(
    permission_id: uuid.UUID,
    body: UpdateVisibilityRequest,
    db: AsyncSession = Depends(get_db),
):
    return await permission_service.update_visibility(db, permission_id, body.visibility)


@router.post("/{permission_id}/share", status_code=201)
async def share_resource(
    permission_id: uuid.UUID,
    body: ShareRequest,
    user_id: uuid.UUID = Depends(_get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await permission_service.share_resource(
        db,
        permission_id=permission_id,
        grantee_type=body.grantee_type,
        grantee_id=body.grantee_id,
        permission=body.permission,
        granted_by=user_id,
    )
    return {"status": "ok"}


@router.delete("/{permission_id}/share")
async def revoke_share(
    permission_id: uuid.UUID,
    body: ShareRequest,
    db: AsyncSession = Depends(get_db),
):
    await permission_service.revoke_share(
        db,
        permission_id=permission_id,
        grantee_type=body.grantee_type,
        grantee_id=body.grantee_id,
    )
    return {"status": "ok"}


@router.get("/resource/{service_name}/{resource_type}/{resource_id}", response_model=ResourcePermissionResponse)
async def get_resource_acl(
    service_name: str,
    resource_type: str,
    resource_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    perm = await permission_service.get_resource_permission(db, service_name, resource_type, resource_id)
    if not perm:
        raise HTTPException(status_code=404, detail="Resource not found")
    return perm
