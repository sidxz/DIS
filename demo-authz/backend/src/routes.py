"""Team Notes API routes — AuthZ mode demo.

In AuthZ mode, the middleware validates two tokens on each request:
  - IdP token (Authorization: Bearer <idp_token>) — proves identity
  - Authz token (X-Authz-Token: <authz_token>) — proves authorization

The client app handles IdP login directly (e.g. Google Sign-In) and calls
Sentinel's /authz/resolve to get the authz token. Both tokens are sent
to this backend on every request.
"""

import uuid
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sentinel_auth.types import AuthenticatedUser

from src.config import sentinel
from src.deps import get_current_user, get_workspace_id, require_role
from src.models import notes

router = APIRouter()


# ---------------------------------------------------------------------------
# Auth — proxy to Sentinel's /authz/resolve (no authz token needed yet)
# ---------------------------------------------------------------------------
class ResolveRequest(BaseModel):
    idp_token: str
    provider: str
    workspace_id: str | None = None


@router.post("/auth/resolve")
async def auth_resolve(body: ResolveRequest):
    """Proxy to Sentinel's /authz/resolve. Adds service key server-side."""
    result = await sentinel.authz.resolve(
        idp_token=body.idp_token,
        provider=body.provider,
        workspace_id=uuid.UUID(body.workspace_id) if body.workspace_id else None,
    )
    return result


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------
class CreateNoteRequest(BaseModel):
    title: str
    content: str


class UpdateNoteRequest(BaseModel):
    title: str | None = None
    content: str | None = None


class ShareNoteRequest(BaseModel):
    user_id: uuid.UUID
    permission: str = "view"


# ---------------------------------------------------------------------------
# User info — extracted from dual tokens by AuthzMiddleware
# ---------------------------------------------------------------------------
@router.get("/me")
async def whoami(user: AuthenticatedUser = Depends(get_current_user)):
    """Current user context from dual-token validation."""
    return {
        "user_id": str(user.user_id),
        "email": user.email,
        "name": user.name,
        "workspace_id": str(user.workspace_id),
        "workspace_slug": user.workspace_slug,
        "workspace_role": user.workspace_role,
    }


# ---------------------------------------------------------------------------
# Tier 1: Workspace role — list notes (any authenticated user)
# ---------------------------------------------------------------------------
@router.get("/notes")
async def list_notes(workspace_id: uuid.UUID = Depends(get_workspace_id)):
    """List all notes in the current workspace."""
    return [asdict(n) for n in notes.list_by_workspace(workspace_id)]


# ---------------------------------------------------------------------------
# Tier 2: Custom RBAC — export notes (requires notes:export action)
# ---------------------------------------------------------------------------
@router.get("/notes/export")
async def export_notes(
    user: AuthenticatedUser = Depends(sentinel.require_action("notes:export")),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    """Export all workspace notes. Requires 'notes:export' RBAC action."""
    workspace_notes = notes.list_by_workspace(workspace_id)
    return {
        "format": "json",
        "count": len(workspace_notes),
        "notes": [asdict(n) for n in workspace_notes],
    }


# ---------------------------------------------------------------------------
# Tier 1: Workspace role — create note (editor+)
# Tier 3: Entity ACL — registers resource with PermissionClient
# ---------------------------------------------------------------------------
@router.post("/notes", status_code=201)
async def create_note(
    body: CreateNoteRequest,
    user: AuthenticatedUser = Depends(require_role("editor")),
):
    """Create a note. Requires at least 'editor' workspace role."""
    note = notes.create(
        title=body.title,
        content=body.content,
        workspace_id=user.workspace_id,
        owner_id=user.user_id,
        owner_name=user.name,
    )

    await sentinel.permissions.register_resource(
        resource_type="note",
        resource_id=note.id,
        workspace_id=user.workspace_id,
        owner_id=user.user_id,
        visibility="workspace",
    )

    return asdict(note)


# ---------------------------------------------------------------------------
# Tier 1: Workspace role — delete note (admin+)
# ---------------------------------------------------------------------------
@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: uuid.UUID,
    user: AuthenticatedUser = Depends(require_role("admin")),
):
    """Delete a note. Requires at least 'admin' workspace role."""
    if not notes.delete(note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"ok": True}
