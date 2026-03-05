# Permission Endpoints

> **Tip:** For interactive API exploration, visit `/docs` (Swagger UI) when the service is running.

The permission endpoints implement a Zanzibar-style resource permission system. They allow backend services to register resources, check permissions, manage sharing, and query accessible resources. All routes are under the `/permissions` prefix.

Permission endpoints use two authentication tiers:

- **Dual auth** (Service Key + JWT): For user-facing operations where the calling service acts on behalf of a user.
- **Service-only auth** (Service Key): For backend operations where the service manages resources directly.

## Endpoints Overview

| Method | Path | Auth Tier | Description |
|---|---|---|---|
| `POST` | `/permissions/check` | Dual | Check permissions for resources |
| `POST` | `/permissions/accessible` | Dual | List accessible resource IDs |
| `POST` | `/permissions/{id}/share` | Dual | Share a resource |
| `POST` | `/permissions/register` | Service-only | Register a new resource |
| `PATCH` | `/permissions/{id}/visibility` | Service-only | Update resource visibility |
| `DELETE` | `/permissions/{id}/share` | Service-only | Revoke a share |
| `GET` | `/permissions/resource/{service}/{type}/{id}` | Service-only | Get resource ACL |

---

## Dual Auth Endpoints

These endpoints require both the `X-Service-Key` header and a JWT `Authorization` header. The service key authenticates the calling service, and the JWT identifies the user on whose behalf the request is made.

### Check Permissions

Checks whether the current user has the specified permissions on one or more resources. Evaluates ownership, workspace visibility, group shares, and direct user shares.

```
POST /permissions/check
```

**Request Body:** [PermissionCheckRequest](schemas.md#permissioncheckrequest)

```json
{
  "checks": [
    {
      "service_name": "docu-store",
      "resource_type": "document",
      "resource_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "action": "view"
    },
    {
      "service_name": "docu-store",
      "resource_type": "document",
      "resource_id": "d4e5f6a7-b8c9-0123-def0-234567890123",
      "action": "edit"
    }
  ]
}
```

**Response** `200 OK` -- [PermissionCheckResponse](schemas.md#permissioncheckresponse)

```json
{
  "results": [
    {
      "service_name": "docu-store",
      "resource_type": "document",
      "resource_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "action": "view",
      "allowed": true
    },
    {
      "service_name": "docu-store",
      "resource_type": "document",
      "resource_id": "d4e5f6a7-b8c9-0123-def0-234567890123",
      "action": "edit",
      "allowed": false
    }
  ]
}
```

**curl example:**

```bash
curl -X POST http://localhost:9003/permissions/check \
  -H "X-Service-Key: sk_your_service_key" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{
    "checks": [
      {
        "service_name": "docu-store",
        "resource_type": "document",
        "resource_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
        "action": "view"
      }
    ]
  }'
```

---

### List Accessible Resources

Returns a list of resource IDs that the current user can access with the specified action within a workspace. If the user has a workspace role that grants blanket access (e.g., admin/owner for edit, any member for view on workspace-visible resources), `has_full_access` is `true`.

```
POST /permissions/accessible
```

**Request Body:** [AccessibleResourcesRequest](schemas.md#accessibleresourcesrequest)

```json
{
  "service_name": "docu-store",
  "resource_type": "document",
  "action": "view",
  "workspace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "limit": 100
}
```

**Response** `200 OK` -- [AccessibleResourcesResponse](schemas.md#accessibleresourcesresponse)

```json
{
  "resource_ids": [
    "c3d4e5f6-a7b8-9012-cdef-123456789012",
    "d4e5f6a7-b8c9-0123-def0-234567890123"
  ],
  "has_full_access": false
}
```

**Errors:**

| Code | Detail |
|---|---|
| `403` | Cross-workspace lookup not allowed (JWT workspace must match request workspace) |

**curl example:**

```bash
curl -X POST http://localhost:9003/permissions/accessible \
  -H "X-Service-Key: sk_your_service_key" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "docu-store",
    "resource_type": "document",
    "action": "view",
    "workspace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }'
```

---

### Share Resource

Grants a user or group access to a resource. The `permission_id` is the ID of the resource permission record (returned by `/permissions/register`).

```
POST /permissions/{permission_id}/share
```

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `permission_id` | path | UUID | Yes | Resource permission record ID |

**Request Body:** [ShareRequest](schemas.md#sharerequest)

```json
{
  "grantee_type": "user",
  "grantee_id": "660e8400-e29b-41d4-a716-446655440001",
  "permission": "view"
}
```

**Response** `201 Created`

```json
{
  "status": "ok"
}
```

**curl example:**

```bash
curl -X POST http://localhost:9003/permissions/e5f6a7b8-c9d0-1234-ef01-345678901234/share \
  -H "X-Service-Key: sk_your_service_key" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{
    "grantee_type": "group",
    "grantee_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "permission": "edit"
  }'
```

---

## Service-Only Endpoints

These endpoints require only the `X-Service-Key` header. No JWT is needed. They are intended for backend service-to-service communication.

### Register Resource

Registers a new resource in the permission system. This should be called by the owning service when a resource is created.

```
POST /permissions/register
```

**Request Body:** [RegisterResourceRequest](schemas.md#registerresourcerequest)

```json
{
  "service_name": "docu-store",
  "resource_type": "document",
  "resource_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "workspace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "owner_id": "550e8400-e29b-41d4-a716-446655440000",
  "visibility": "workspace"
}
```

**Response** `201 Created` -- [ResourcePermissionResponse](schemas.md#resourcepermissionresponse)

```json
{
  "id": "e5f6a7b8-c9d0-1234-ef01-345678901234",
  "service_name": "docu-store",
  "resource_type": "document",
  "resource_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "workspace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "owner_id": "550e8400-e29b-41d4-a716-446655440000",
  "visibility": "workspace",
  "created_at": "2025-07-01T14:00:00Z",
  "shares": []
}
```

**curl example:**

```bash
curl -X POST http://localhost:9003/permissions/register \
  -H "X-Service-Key: sk_your_service_key" \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "docu-store",
    "resource_type": "document",
    "resource_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
    "workspace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "owner_id": "550e8400-e29b-41d4-a716-446655440000",
    "visibility": "workspace"
  }'
```

---

### Update Visibility

Changes the visibility of a registered resource between `private` and `workspace`.

```
PATCH /permissions/{permission_id}/visibility
```

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `permission_id` | path | UUID | Yes | Resource permission record ID |

**Request Body:** [UpdateVisibilityRequest](schemas.md#updatevisibilityrequest)

```json
{
  "visibility": "private"
}
```

**Response** `200 OK` -- [ResourcePermissionResponse](schemas.md#resourcepermissionresponse)

**curl example:**

```bash
curl -X PATCH http://localhost:9003/permissions/e5f6a7b8-c9d0-1234-ef01-345678901234/visibility \
  -H "X-Service-Key: sk_your_service_key" \
  -H "Content-Type: application/json" \
  -d '{"visibility": "private"}'
```

---

### Revoke Share

Removes a previously granted share from a resource. The `permission` field in the body is required by the schema but only `grantee_type` and `grantee_id` are used for matching.

```
DELETE /permissions/{permission_id}/share
```

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `permission_id` | path | UUID | Yes | Resource permission record ID |

**Request Body:** [ShareRequest](schemas.md#sharerequest)

```json
{
  "grantee_type": "user",
  "grantee_id": "660e8400-e29b-41d4-a716-446655440001",
  "permission": "view"
}
```

**Response** `200 OK`

```json
{
  "status": "ok"
}
```

**curl example:**

```bash
curl -X DELETE http://localhost:9003/permissions/e5f6a7b8-c9d0-1234-ef01-345678901234/share \
  -H "X-Service-Key: sk_your_service_key" \
  -H "Content-Type: application/json" \
  -d '{
    "grantee_type": "user",
    "grantee_id": "660e8400-e29b-41d4-a716-446655440001",
    "permission": "view"
  }'
```

---

### Get Resource ACL

Retrieves the full permission record for a resource, including all shares.

```
GET /permissions/resource/{service_name}/{resource_type}/{resource_id}
```

| Parameter | In | Type | Required | Description |
|---|---|---|---|---|
| `service_name` | path | string | Yes | Service name (e.g., `docu-store`) |
| `resource_type` | path | string | Yes | Resource type (e.g., `document`) |
| `resource_id` | path | UUID | Yes | Resource ID |

**Response** `200 OK` -- [ResourcePermissionResponse](schemas.md#resourcepermissionresponse)

```json
{
  "id": "e5f6a7b8-c9d0-1234-ef01-345678901234",
  "service_name": "docu-store",
  "resource_type": "document",
  "resource_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "workspace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "owner_id": "550e8400-e29b-41d4-a716-446655440000",
  "visibility": "workspace",
  "created_at": "2025-07-01T14:00:00Z",
  "shares": [
    {
      "id": "f6a7b8c9-d0e1-2345-f012-456789012345",
      "grantee_type": "group",
      "grantee_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "permission": "edit",
      "granted_by": "550e8400-e29b-41d4-a716-446655440000",
      "granted_at": "2025-07-02T09:00:00Z"
    }
  ]
}
```

**Errors:**

| Code | Detail |
|---|---|
| `404` | Resource not found |

**curl example:**

```bash
curl http://localhost:9003/permissions/resource/docu-store/document/c3d4e5f6-a7b8-9012-cdef-123456789012 \
  -H "X-Service-Key: sk_your_service_key"
```
