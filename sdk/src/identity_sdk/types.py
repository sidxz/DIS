import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: uuid.UUID
    email: str
    name: str
    workspace_id: uuid.UUID
    workspace_slug: str
    workspace_role: str  # 'owner' | 'admin' | 'editor' | 'viewer'
    groups: list[uuid.UUID] = field(default_factory=list)

    @property
    def is_admin(self) -> bool:
        return self.workspace_role in ("admin", "owner")

    @property
    def is_editor(self) -> bool:
        return self.workspace_role in ("editor", "admin", "owner")

    def has_role(self, minimum_role: str) -> bool:
        hierarchy = {"viewer": 0, "editor": 1, "admin": 2, "owner": 3}
        return hierarchy.get(self.workspace_role, -1) >= hierarchy.get(minimum_role, 99)


@dataclass(frozen=True)
class WorkspaceContext:
    workspace_id: uuid.UUID
    workspace_slug: str
    user_id: uuid.UUID
    role: str
