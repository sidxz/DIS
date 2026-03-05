# Service-to-Service Authentication

Consuming applications authenticate with the Identity Service using the `X-Service-Key` header. This mechanism ensures that only authorized backend services can call permission endpoints, while also allowing the service to identify which application is making the request.

## X-Service-Key Header

Every request to the `/permissions/*` endpoints must include a valid service API key:

```
X-Service-Key: your-secret-key-here
```

The Identity Service validates the key against the configured set of allowed keys. If the key is missing or invalid, the request is rejected with `401 Unauthorized`.

## Auth Tiers

Permission endpoints use two authentication tiers depending on the operation:

| Tier | Authentication Required | Endpoints |
|------|------------------------|-----------|
| **Dual auth** | `X-Service-Key` + user `Authorization: Bearer` JWT | `POST /permissions/check` |
| | | `POST /permissions/accessible` |
| | | `POST /permissions/{id}/share` |
| **Service-only** | `X-Service-Key` only | `POST /permissions/register` |
| | | `PATCH /permissions/{id}/visibility` |
| | | `DELETE /permissions/{id}/share` |
| | | `GET /permissions/resource/{service}/{type}/{id}` |

### Dual Auth Endpoints

These endpoints need both a service key (to authenticate the calling service) and a user JWT (to identify the user whose permissions are being checked or modified). The user context (user ID, workspace ID, workspace role, groups) is extracted from the JWT.

Example request:

```bash
curl -X POST https://identity.example.com/permissions/check \
  -H "X-Service-Key: sk_live_abc123" \
  -H "Authorization: Bearer eyJhbGciOi..." \
  -H "Content-Type: application/json" \
  -d '{
    "checks": [{
      "service_name": "docu-store",
      "resource_type": "document",
      "resource_id": "doc-uuid",
      "action": "edit"
    }]
  }'
```

### Service-Only Endpoints

These endpoints perform administrative operations on behalf of the service (registering resources, managing visibility, revoking shares). They do not require a user JWT because the action is taken by the service itself, not on behalf of a specific user.

Example request:

```bash
curl -X POST https://identity.example.com/permissions/register \
  -H "X-Service-Key: sk_live_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "docu-store",
    "resource_type": "document",
    "resource_id": "new-doc-uuid",
    "workspace_id": "workspace-uuid",
    "owner_id": "creator-user-uuid",
    "visibility": "workspace"
  }'
```

## Dev Mode

When the `SERVICE_API_KEYS` environment variable is empty (the default), the service key requirement is disabled entirely. All requests pass through the `require_service_key` dependency without validation.

This makes local development easier -- you do not need to configure service keys to test permission endpoints.

```
# .env (development)
SERVICE_API_KEYS=

# .env (production)
SERVICE_API_KEYS=sk_live_abc123,sk_live_def456
```

**Important**: In production, always set `SERVICE_API_KEYS` to a non-empty comma-separated list of valid keys. An empty value means no enforcement, which effectively disables service authentication.

## Production Configuration

### Generating Keys

Generate a cryptographically secure API key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

This produces a 43-character URL-safe string like `dBjftJeZ4CVP-mB92pU4hQVOs0w7Iq6pHqg_8RbYFVc`.

### Configuring Multiple Keys

Multiple keys are separated by commas. This allows key rotation without downtime -- add the new key, deploy to all services, then remove the old key.

```
SERVICE_API_KEYS=sk_live_abc123,sk_live_def456
```

### Key Rotation Procedure

1. Generate a new key.
2. Add it to `SERVICE_API_KEYS` alongside the existing key: `SERVICE_API_KEYS=old_key,new_key`.
3. Deploy the Identity Service with both keys active.
4. Update all consuming services to use the new key.
5. Remove the old key: `SERVICE_API_KEYS=new_key`.
6. Deploy the Identity Service again.

## SDK Integration

The Python SDK's `PermissionClient` handles service key headers automatically:

```python
from sentinel_auth import PermissionClient

client = PermissionClient(
    base_url="https://identity.example.com",
    service_name="docu-store",
    service_key="sk_live_abc123",
)

# Dual auth: pass the user's JWT token
result = client.check_permission(
    token="user-jwt-here",
    resource_type="document",
    resource_id="doc-uuid",
    action="edit",
)

# Service-only: no token needed
client.register_resource(
    resource_type="document",
    resource_id="new-doc-uuid",
    workspace_id="workspace-uuid",
    owner_id="creator-uuid",
)
```

The SDK's `_headers(token=None)` method builds the appropriate headers:

- Always includes `X-Service-Key` if a `service_key` was provided.
- Includes `Authorization: Bearer {token}` when a user token is passed.
