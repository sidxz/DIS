import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.workspace import (
    InviteMemberRequest,
    UpdateMemberRoleRequest,
    WorkspaceCreateRequest,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceUpdateRequest,
)
from src.services import workspace_service

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


# TODO: replace with JWT-based dependency
async def _get_current_user_id() -> uuid.UUID:
    raise HTTPException(status_code=401, detail="Not authenticated")


@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    body: WorkspaceCreateRequest,
    user_id: uuid.UUID = Depends(_get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    workspace = await workspace_service.create_workspace(
        db, name=body.name, slug=body.slug, created_by=user_id, description=body.description
    )
    return workspace


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    user_id: uuid.UUID = Depends(_get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await workspace_service.list_user_workspaces(db, user_id)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    workspace = await workspace_service.get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: uuid.UUID,
    body: WorkspaceUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    # TODO: check admin/owner role
    return await workspace_service.update_workspace(db, workspace_id, name=body.name, description=body.description)


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    # TODO: check owner role
    await workspace_service.delete_workspace(db, workspace_id)


# --- Members ---


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberResponse])
async def list_members(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await workspace_service.list_members(db, workspace_id)


@router.post("/{workspace_id}/members/invite", response_model=WorkspaceMemberResponse, status_code=201)
async def invite_member(
    workspace_id: uuid.UUID,
    body: InviteMemberRequest,
    db: AsyncSession = Depends(get_db),
):
    # TODO: check admin/owner role
    membership = await workspace_service.invite_member(db, workspace_id, email=body.email, role=body.role)
    return membership


@router.patch("/{workspace_id}/members/{user_id}")
async def update_member_role(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    body: UpdateMemberRoleRequest,
    db: AsyncSession = Depends(get_db),
):
    # TODO: check admin/owner role
    return await workspace_service.update_member_role(db, workspace_id, user_id, role=body.role)


@router.delete("/{workspace_id}/members/{user_id}", status_code=204)
async def remove_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    # TODO: check admin/owner role
    await workspace_service.remove_member(db, workspace_id, user_id)
