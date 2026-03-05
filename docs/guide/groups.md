# Groups

Groups are named collections of users within a workspace. They serve as the primary mechanism for granting permissions to multiple users at once -- instead of sharing a resource with ten individual users, you share it with a group.

## Purpose

- **Batch permission grants**: Share a resource (view or edit) with an entire group instead of individual users.
- **Organizational structure**: Model teams, departments, or project groups within a workspace.
- **JWT-embedded**: Group IDs are included in the user's access token, enabling fast permission resolution without additional database lookups during the `check_permission` flow.

## CRUD Operations

All group operations are scoped to a workspace and require admin or owner role.

| Operation | Endpoint | Required Role |
|-----------|----------|---------------|
| Create | `POST /workspaces/{workspace_id}/groups` | Admin+ |
| List | `GET /workspaces/{workspace_id}/groups` | Any member |
| Update | `PATCH /workspaces/{workspace_id}/groups/{group_id}` | Admin+ |
| Delete | `DELETE /workspaces/{workspace_id}/groups/{group_id}` | Admin+ |

### Creating a Group

```
POST /workspaces/{workspace_id}/groups
{
  "name": "Engineering",
  "description": "Backend and frontend engineers"
}
```

Group names must be unique within a workspace. The `(workspace_id, name)` pair has a unique constraint in the database.

### Listing Groups

```
GET /workspaces/{workspace_id}/groups
```

Returns all groups in the workspace. Any workspace member can list groups, but only admins and owners can create, update, or delete them.

## Member Management

Adding and removing group members requires admin or owner role.

### Adding a Member

```
POST /workspaces/{workspace_id}/groups/{group_id}/members/{user_id}
```

The user must be a member of the workspace. A user can belong to multiple groups within the same workspace.

### Removing a Member

```
DELETE /workspaces/{workspace_id}/groups/{group_id}/members/{user_id}
```

Removing a user from a group does not remove them from the workspace. It only removes their group membership.

## Relationship to Permissions

Groups are one of the two grantee types in the [permission system](permissions.md). When a resource is shared with a group, all members of that group receive the granted permission level (`view` or `edit`).

### How Group Permissions Are Resolved

1. When tokens are issued, the service queries all groups the user belongs to in the current workspace and embeds the group IDs in the JWT's `groups` claim.

2. When `check_permission` is called, it receives the `group_ids` from the JWT and checks the `resource_shares` table for any shares where `grantee_type = 'group'` and `grantee_id IN (user's group IDs)`.

3. If any group share matches the requested action, access is granted.

```json
// Example JWT groups claim
{
  "groups": [
    "a1b2c3d4-0000-0000-0000-000000000001",
    "a1b2c3d4-0000-0000-0000-000000000002"
  ]
}
```

### Share Example

Granting edit access to the "Engineering" group on a document:

```
POST /permissions/{permission_id}/share
X-Service-Key: your-service-key
Authorization: Bearer {user-jwt}

{
  "grantee_type": "group",
  "grantee_id": "a1b2c3d4-0000-0000-0000-000000000001",
  "permission": "edit"
}
```

After this share is created, any user whose JWT contains this group ID in the `groups` claim will have edit access to the resource.

## Important Notes

- **Group membership changes require re-authentication**: Since group IDs are embedded in the JWT, adding or removing a user from a group only takes effect when the user's token is next refreshed or re-issued.
- **Deleting a group** cascades to all `group_memberships` for that group. Any `resource_shares` granted to the group will reference a non-existent grantee and will no longer match during permission checks.
- **Groups are workspace-scoped**: A group in workspace A is completely separate from a group in workspace B, even if they share the same name.
