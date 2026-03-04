import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.group import GroupCreateRequest, GroupMemberResponse, GroupResponse, GroupUpdateRequest
from src.services import group_service

router = APIRouter(prefix="/workspaces/{workspace_id}/groups", tags=["groups"])


# TODO: replace with JWT-based dependency
async def _get_current_user_id() -> uuid.UUID:
    raise HTTPException(status_code=401, detail="Not authenticated")


@router.post("", response_model=GroupResponse, status_code=201)
async def create_group(
    workspace_id: uuid.UUID,
    body: GroupCreateRequest,
    user_id: uuid.UUID = Depends(_get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await group_service.create_group(
        db, workspace_id=workspace_id, name=body.name, created_by=user_id, description=body.description
    )


@router.get("", response_model=list[GroupResponse])
async def list_groups(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await group_service.list_groups(db, workspace_id)


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: uuid.UUID,
    body: GroupUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    return await group_service.update_group(db, group_id, name=body.name, description=body.description)


@router.delete("/{group_id}", status_code=204)
async def delete_group(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await group_service.delete_group(db, group_id)


@router.post("/{group_id}/members/{user_id}", status_code=201)
async def add_group_member(
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await group_service.add_member(db, group_id, user_id)
    return {"status": "ok"}


@router.delete("/{group_id}/members/{user_id}", status_code=204)
async def remove_group_member(
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await group_service.remove_member(db, group_id, user_id)
