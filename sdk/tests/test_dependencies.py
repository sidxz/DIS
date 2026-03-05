"""Tests for FastAPI dependency helpers."""

import uuid

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from sentinel_auth.dependencies import get_current_user, get_workspace_context, get_workspace_id, require_role
from sentinel_auth.types import AuthenticatedUser


def _inject_user(app: FastAPI, user: AuthenticatedUser):
    """Middleware that injects a fake user into request.state (bypass JWT)."""

    @app.middleware("http")
    async def _set_user(request: Request, call_next):
        request.state.user = user
        return await call_next(request)


@pytest.fixture()
def editor_user(user_id, workspace_id):
    return AuthenticatedUser(
        user_id=user_id,
        email="a@b.com",
        name="A",
        workspace_id=workspace_id,
        workspace_slug="acme",
        workspace_role="editor",
    )


class TestGetCurrentUser:
    def test_returns_user(self, editor_user):
        app = FastAPI()
        _inject_user(app, editor_user)

        @app.get("/me")
        def me(user: AuthenticatedUser = Depends(get_current_user)):
            return {"email": user.email}

        resp = TestClient(app).get("/me")
        assert resp.status_code == 200
        assert resp.json()["email"] == "a@b.com"

    def test_401_when_no_user(self):
        app = FastAPI()

        @app.get("/me")
        def me(user: AuthenticatedUser = Depends(get_current_user)):
            return {"email": user.email}

        resp = TestClient(app).get("/me")
        assert resp.status_code == 401


class TestGetWorkspaceId:
    def test_returns_workspace_id(self, editor_user, workspace_id):
        app = FastAPI()
        _inject_user(app, editor_user)

        @app.get("/wid")
        def wid(wid: uuid.UUID = Depends(get_workspace_id)):
            return {"wid": str(wid)}

        resp = TestClient(app).get("/wid")
        assert resp.json()["wid"] == str(workspace_id)


class TestGetWorkspaceContext:
    def test_returns_context(self, editor_user, workspace_id, user_id):
        app = FastAPI()
        _inject_user(app, editor_user)

        @app.get("/ctx")
        def ctx(ctx=Depends(get_workspace_context)):
            return {"wid": str(ctx.workspace_id), "role": ctx.role}

        resp = TestClient(app).get("/ctx")
        data = resp.json()
        assert data["wid"] == str(workspace_id)
        assert data["role"] == "editor"


class TestRequireRole:
    def test_passes_when_role_sufficient(self, editor_user):
        app = FastAPI()
        _inject_user(app, editor_user)

        @app.get("/edit")
        def edit(user: AuthenticatedUser = Depends(require_role("editor"))):
            return {"ok": True}

        assert TestClient(app).get("/edit").status_code == 200

    def test_rejects_when_role_insufficient(self, editor_user):
        app = FastAPI()
        _inject_user(app, editor_user)

        @app.get("/admin")
        def admin(user: AuthenticatedUser = Depends(require_role("admin"))):
            return {"ok": True}

        resp = TestClient(app).get("/admin")
        assert resp.status_code == 403
        assert "admin" in resp.json()["detail"]
