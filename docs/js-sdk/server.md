# Server Utilities

The `@sentinel-auth/js/server` entry point provides Node.js and Edge-compatible utilities for JWT verification, Zanzibar-style permission checks, and RBAC action checks. These mirror the Python SDK's server-side clients.

```typescript
import { verifyToken, PermissionClient, RoleClient } from '@sentinel-auth/js/server'
```

## JWT Verification

Verify Sentinel JWTs using JWKS (JSON Web Key Set). Uses the `jose` library, which works in Node.js, Edge runtimes, and Cloudflare Workers.

### `verifyToken`

```typescript
import { verifyToken, payloadToUser } from '@sentinel-auth/js/server'

const payload = await verifyToken(token, {
  jwksUrl: 'http://localhost:9003/.well-known/jwks.json',
})

// Map JWT claims to a SentinelUser object
const user = payloadToUser(payload)
```

### Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `jwksUrl` | `string` | *required* | URL to the Sentinel JWKS endpoint |
| `audience` | `string` | `"sentinel:access"` | Expected `aud` claim |
| `issuer` | `string` | — | Expected `iss` claim |

JWKS keys are fetched and cached automatically by `jose`. The first call may be slower due to the key fetch; subsequent calls use the cached key set.

### `payloadToUser`

Maps the verified JWT payload to a `SentinelUser` object:

```typescript
const user = payloadToUser(payload)
// { userId, email, name, workspaceId, workspaceSlug, workspaceRole, groups }
```

JWT claim mapping:

| JWT Claim | User Field |
|-----------|------------|
| `sub` | `userId` |
| `email` | `email` |
| `name` | `name` |
| `wid` | `workspaceId` |
| `wslug` | `workspaceSlug` |
| `wrole` | `workspaceRole` |
| `groups` | `groups` |

---

## Permission Client

Server-side client for the Sentinel Zanzibar-style permission API. Mirrors the Python SDK's `PermissionClient`.

### Setup

```typescript
import { PermissionClient } from '@sentinel-auth/js/server'

const permissions = new PermissionClient(
  'http://localhost:9003',   // Sentinel base URL
  'my-service',              // Your service name
  'sk_my_service_key',       // Service API key (optional)
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `baseUrl` | `string` | Yes | Base URL of the Sentinel service |
| `serviceName` | `string` | Yes | Your service's registered name |
| `serviceKey` | `string` | No | Service API key for `X-Service-Key` header |

### `can`

Check a single permission. Returns `true` or `false`.

```typescript
const allowed = await permissions.can(token, 'document', docId, 'view')
if (!allowed) throw new Error('Forbidden')
```

### `check`

Batch check multiple permissions in a single request.

```typescript
const results = await permissions.check(token, [
  { service_name: 'my-service', resource_type: 'document', resource_id: docId, action: 'view' },
  { service_name: 'my-service', resource_type: 'document', resource_id: docId, action: 'edit' },
])
// [{ ...check, allowed: true }, { ...check, allowed: false }]
```

### `registerResource`

Register a new resource with the permission system. Requires a service key.

```typescript
await permissions.registerResource({
  service_name: 'my-service',
  resource_type: 'document',
  resource_id: docId,
  workspace_id: workspaceId,
  owner_id: userId,
  visibility: 'workspace',  // 'private' | 'workspace' | 'public'
})
```

### `share`

Share a resource with a user or group.

```typescript
await permissions.share(token, 'document', docId, {
  grantee_type: 'user',    // 'user' | 'group'
  grantee_id: targetUserId,
  permission: 'edit',       // 'view' | 'edit' | 'manage'
})
```

### `accessible`

List resource IDs the current user can access.

```typescript
const result = await permissions.accessible(
  token,
  'document',    // resource type
  'view',        // action
  workspaceId,
  100,           // limit (optional)
)
// { resource_ids: ['doc1', 'doc2'], has_full_access: false }
```

---

## Role Client

Server-side client for the Sentinel RBAC role/action API. Mirrors the Python SDK's `RoleClient`.

### Setup

```typescript
import { RoleClient } from '@sentinel-auth/js/server'

const roles = new RoleClient(
  'http://localhost:9003',   // Sentinel base URL
  'my-service',              // Your service name
  'sk_my_service_key',       // Service API key (optional)
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `baseUrl` | `string` | Yes | Base URL of the Sentinel service |
| `serviceName` | `string` | Yes | Your service's registered name |
| `serviceKey` | `string` | No | Service API key for `X-Service-Key` header |

### `registerActions`

Register actions for your service. Typically called at application startup.

```typescript
await roles.registerActions([
  { action: 'notes:create', description: 'Create new notes' },
  { action: 'notes:export', description: 'Export notes to PDF' },
  { action: 'reports:view', description: 'View analytics reports' },
])
```

### `checkAction`

Check if a user can perform an action in a workspace.

```typescript
const allowed = await roles.checkAction(token, 'notes:export', workspaceId)
if (!allowed) throw new Error('Forbidden')
```

### `getUserActions`

List all actions the user can perform in a workspace.

```typescript
const actions = await roles.getUserActions(token, workspaceId)
// ['notes:create', 'notes:export', 'reports:view']
```

---

## Express Example

```typescript
import express from 'express'
import { verifyToken, payloadToUser, PermissionClient } from '@sentinel-auth/js/server'

const app = express()
const permissions = new PermissionClient(
  'http://localhost:9003',
  'my-service',
  process.env.SERVICE_KEY,
)

// Auth middleware
async function authenticate(req, res, next) {
  const token = req.headers.authorization?.replace('Bearer ', '')
  if (!token) return res.status(401).json({ error: 'Unauthorized' })

  try {
    const payload = await verifyToken(token, {
      jwksUrl: 'http://localhost:9003/.well-known/jwks.json',
    })
    req.user = payloadToUser(payload)
    req.token = token
    next()
  } catch {
    res.status(401).json({ error: 'Invalid token' })
  }
}

// Permission-protected route
app.get('/api/documents/:id', authenticate, async (req, res) => {
  const allowed = await permissions.can(req.token, 'document', req.params.id, 'view')
  if (!allowed) return res.status(403).json({ error: 'Forbidden' })

  const doc = await getDocument(req.params.id)
  res.json(doc)
})
```

## Next Steps

- [Auth Client](auth-client.md) -- browser-side auth client
- [React Integration](react.md) -- React provider and hooks
- [Next.js Integration](nextjs.md) -- Edge Middleware and server helpers
