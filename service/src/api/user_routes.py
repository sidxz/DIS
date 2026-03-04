import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.user import UserResponse, UserUpdateRequest
from src.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


# TODO: replace with JWT-based dependency
async def _get_current_user_id() -> uuid.UUID:
    raise HTTPException(status_code=401, detail="Not authenticated")


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: uuid.UUID = Depends(_get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdateRequest,
    user_id: uuid.UUID = Depends(_get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.update_user(db, user_id, name=body.name, avatar_url=body.avatar_url)
    return user
