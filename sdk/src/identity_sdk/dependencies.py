"""FastAPI dependency helpers for extracting auth context from requests."""

import uuid
from collections.abc import Callable
from functools import wraps

from fastapi import Depends, HTTPException, Request

from identity_sdk.types import AuthenticatedUser, WorkspaceContext


def get_current_user(request: Request) -> AuthenticatedUser:
    """Extract the authenticated user from request state (set by JWTAuthMiddleware)."""
    user: AuthenticatedUser | None = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def get_workspace_id(user: AuthenticatedUser = Depends(get_current_user)) -> uuid.UUID:
    """Extract the workspace ID from the current user's JWT context."""
    return user.workspace_id


def get_workspace_context(user: AuthenticatedUser = Depends(get_current_user)) -> WorkspaceContext:
    """Extract full workspace context from the current user's JWT."""
    return WorkspaceContext(
        workspace_id=user.workspace_id,
        workspace_slug=user.workspace_slug,
        user_id=user.user_id,
        role=user.workspace_role,
    )


def require_role(minimum_role: str) -> Callable:
    """Dependency factory that enforces a minimum workspace role.

    Usage:
        @router.post("/things")
        async def create_thing(user: AuthenticatedUser = Depends(require_role("editor"))):
            ...
    """

    def dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not user.has_role(minimum_role):
            raise HTTPException(
                status_code=403,
                detail=f"Requires at least '{minimum_role}' role, you have '{user.workspace_role}'",
            )
        return user

    return dependency
