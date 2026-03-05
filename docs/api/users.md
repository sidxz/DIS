# User Endpoints

> **Tip:** For interactive API exploration, visit `/docs` (Swagger UI) when the service is running.

The user endpoints allow authenticated users to view and update their own profile. All routes are under the `/users` prefix and require a valid JWT Bearer token.

## Endpoints Overview

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/users/me` | JWT | Get current user profile |
| `PATCH` | `/users/me` | JWT | Update current user profile |

---

## Get Current User

Returns the profile of the authenticated user.

```
GET /users/me
```

**Auth:** JWT Bearer token required.

**Response** `200 OK` -- [UserResponse](schemas.md#userresponse)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "jane@example.com",
  "name": "Jane Doe",
  "avatar_url": "https://avatars.example.com/jane.png",
  "is_active": true,
  "created_at": "2025-06-15T10:30:00Z"
}
```

**Errors:**

| Code | Detail |
|---|---|
| `401` | Missing or invalid JWT |
| `404` | User not found |

**curl example:**

```bash
curl http://localhost:9003/users/me \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIs..."
```

---

## Update Current User

Updates the authenticated user's profile fields. Only provided fields are changed; omitted fields remain unchanged.

```
PATCH /users/me
```

**Auth:** JWT Bearer token required.

**Request Body:** [UserUpdateRequest](schemas.md#userupdaterequest)

```json
{
  "name": "Jane Smith",
  "avatar_url": "https://avatars.example.com/jane-new.png"
}
```

Both fields are optional. You can send only the field you want to update:

```json
{
  "name": "Jane Smith"
}
```

**Response** `200 OK` -- [UserResponse](schemas.md#userresponse)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "jane@example.com",
  "name": "Jane Smith",
  "avatar_url": "https://avatars.example.com/jane-new.png",
  "is_active": true,
  "created_at": "2025-06-15T10:30:00Z"
}
```

**Errors:**

| Code | Detail |
|---|---|
| `401` | Missing or invalid JWT |

**curl example:**

```bash
curl -X PATCH http://localhost:9003/users/me \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{"name": "Jane Smith"}'
```
