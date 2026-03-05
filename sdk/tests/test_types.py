"""Tests for AuthenticatedUser and WorkspaceContext."""

import uuid

from sentinel_auth.types import AuthenticatedUser, WorkspaceContext


def _make_user(role: str = "editor") -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=uuid.uuid4(),
        email="a@b.com",
        name="A",
        workspace_id=uuid.uuid4(),
        workspace_slug="slug",
        workspace_role=role,
    )


class TestAuthenticatedUser:
    def test_is_admin_for_owner(self):
        assert _make_user("owner").is_admin is True

    def test_is_admin_for_admin(self):
        assert _make_user("admin").is_admin is True

    def test_is_admin_for_editor(self):
        assert _make_user("editor").is_admin is False

    def test_is_editor_for_editor(self):
        assert _make_user("editor").is_editor is True

    def test_is_editor_for_viewer(self):
        assert _make_user("viewer").is_editor is False

    def test_has_role_hierarchy(self):
        owner = _make_user("owner")
        assert owner.has_role("viewer") is True
        assert owner.has_role("editor") is True
        assert owner.has_role("admin") is True
        assert owner.has_role("owner") is True

    def test_has_role_viewer_cannot_edit(self):
        viewer = _make_user("viewer")
        assert viewer.has_role("viewer") is True
        assert viewer.has_role("editor") is False

    def test_has_role_unknown_role(self):
        user = _make_user("editor")
        assert user.has_role("superadmin") is False

    def test_frozen(self):
        user = _make_user()
        try:
            user.email = "new@b.com"  # type: ignore[misc]
            raise AssertionError("Should have raised")
        except AttributeError:
            pass

    def test_groups_default_empty(self):
        user = _make_user()
        assert user.groups == []


class TestWorkspaceContext:
    def test_construction(self):
        wid = uuid.uuid4()
        uid = uuid.uuid4()
        ctx = WorkspaceContext(workspace_id=wid, workspace_slug="s", user_id=uid, role="admin")
        assert ctx.workspace_id == wid
        assert ctx.role == "admin"
