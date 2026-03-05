# Workspaces

Workspaces are the tenant isolation boundary in the Sentinel Auth. Every user, group, permission, and resource is scoped to a workspace. A user can belong to multiple workspaces, but their JWT token always reflects a single active workspace context.

## What is a Workspace?

A workspace represents an organization, team, or project that groups users and resources together. Key properties:

- **Logical isolation**: All queries are filtered by `workspace_id`. Users in workspace A cannot see or access resources in workspace B.
- **Soft isolation**: All workspaces share the same database and Redis instance. Isolation is enforced at the application layer, not at the infrastructure level.
- **JWT-scoped**: When a user selects a workspace, their access token is issued with that workspace's ID, slug, and their role within it. Switching workspaces requires obtaining a new token.

## CRUD Operations

| Operation | Endpoint | Required Role | Notes |
|-----------|----------|---------------|-------|
| Create | `POST /workspaces` | Any authenticated user | Creator becomes `owner` |
| List | `GET /workspaces` | Any authenticated user | Returns only workspaces the user belongs to |
| Get | `GET /workspaces/{id}` | Member | JWT workspace must match |
| Update | `PATCH /workspaces/{id}` | Admin+ | Update name and description |
| Delete | `DELETE /workspaces/{id}` | Owner | Cascades to memberships, groups, permissions |

## Slug Constraints

Every workspace has a unique slug used in URLs and as a human-readable identifier. Slugs must match the following pattern:

```
^[a-z0-9][a-z0-9-]*[a-z0-9]$
```

Rules:

- Lowercase letters, digits, and hyphens only
- Must start and end with a letter or digit (no leading/trailing hyphens)
- Minimum 2 characters
- Must be unique across all workspaces

Examples of valid slugs: `acme-corp`, `my-team`, `project42`, `a1`

Examples of invalid slugs: `-acme`, `acme-`, `Acme-Corp`, `my_team`

## Member Management

### Inviting Members

Admins and owners can invite existing users to a workspace by email:

```
POST /workspaces/{workspace_id}/members/invite
{
  "email": "alice@example.com",
  "role": "editor"
}
```

The invited user must already exist in the system (they must have logged in at least once via an OAuth provider). The invitation immediately creates a `workspace_membership` record -- there is no pending invitation state.

### Changing Roles

Admins and owners can change a member's role:

```
PATCH /workspaces/{workspace_id}/members/{user_id}
{
  "role": "admin"
}
```

### Removing Members

Admins and owners can remove a member from the workspace:

```
DELETE /workspaces/{workspace_id}/members/{user_id}
```

Removing a member also invalidates their JWT for that workspace on the next token refresh, since the membership record no longer exists.

## Role Hierarchy

Workspaces use a four-tier role hierarchy. Higher roles inherit all permissions of lower roles.

```
Owner > Admin > Editor > Viewer
```

### Permissions Matrix

| Permission | Viewer | Editor | Admin | Owner |
|-----------|--------|--------|-------|-------|
| View workspace details | Yes | Yes | Yes | Yes |
| View all members | Yes | Yes | Yes | Yes |
| View workspace resources | Yes | Yes | Yes | Yes |
| Create resources | No | Yes | Yes | Yes |
| Edit own resources | No | Yes | Yes | Yes |
| Edit all resources | No | No | Yes | Yes |
| Manage members (invite, role change, remove) | No | No | Yes | Yes |
| Update workspace settings | No | No | Yes | Yes |
| Delete workspace | No | No | No | Yes |

### Role Enforcement

Workspace roles are enforced at two levels:

1. **API layer**: Route handlers call `_require_role(user, minimum_role)` which compares the role from the JWT against the required minimum using a numeric hierarchy (`viewer=0`, `editor=1`, `admin=2`, `owner=3`).

2. **Permission system**: The `check_permission` function grants admin and owner roles full access to all resources in the workspace, regardless of explicit shares or visibility settings. See [Permissions](permissions.md) for details.

## Workspace Context in JWT

When a user selects a workspace and tokens are issued, the access token includes:

```json
{
  "wid": "550e8400-e29b-41d4-a716-446655440000",
  "wslug": "acme-corp",
  "wrole": "editor",
  "groups": ["group-uuid-1", "group-uuid-2"]
}
```

The `wid` (workspace ID) is checked on every workspace-scoped API call to ensure the user is operating within their current workspace context. Cross-workspace requests are rejected with `403 Forbidden`.
