# Server Utilities

`@sentinel-auth/js/server` provides JWT verification, permission checks, and RBAC action checks for Node.js and Edge runtimes.

```typescript
import { verifyToken, payloadToUser, PermissionClient, RoleClient } from '@sentinel-auth/js/server'
```

## verifyToken

Verify a Sentinel JWT against a JWKS endpoint. Uses `jose` (Edge-compatible).

```typescript
const payload = await verifyToken(token, {
  jwksUrl: 'http://localhost:9003/.well-known/jwks.json',
})
const user = payloadToUser(payload)
// { userId, email, name, workspaceId, workspaceSlug, workspaceRole, groups }
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `jwksUrl` | `string` | required | Sentinel JWKS endpoint |
| `audience` | `string` | `"sentinel:access"` | Expected `aud` claim |
| `issuer` | `string` | -- | Expected `iss` claim |

JWKS keys are fetched and cached automatically.

## PermissionClient

Zanzibar-style permission checks. Mirrors the Python SDK.

```typescript
const permissions = new PermissionClient(
  'http://localhost:9003', 'my-service', 'sk_my_service_key',
)
```

**can(token, resourceType, resourceId, action)** -- single permission check.

```typescript
const allowed = await permissions.can(token, 'document', docId, 'view')
```

**check(token, checks)** -- batch check.

```typescript
const results = await permissions.check(token, [
  { service_name: 'my-service', resource_type: 'document', resource_id: docId, action: 'view' },
  { service_name: 'my-service', resource_type: 'document', resource_id: docId, action: 'edit' },
])
```

**registerResource(request)** -- register a resource (service key, no JWT needed).

```typescript
await permissions.registerResource({
  service_name: 'my-service', resource_type: 'document', resource_id: docId,
  workspace_id: workspaceId, owner_id: userId, visibility: 'workspace',
})
```

**share(token, resourceType, resourceId, share)** -- grant access.

```typescript
await permissions.share(token, 'document', docId, {
  grantee_type: 'user', grantee_id: targetUserId, permission: 'edit',
})
```

**accessible(token, resourceType, action, workspaceId, limit?)** -- list accessible resource IDs.

```typescript
const result = await permissions.accessible(token, 'document', 'view', workspaceId)
// { resource_ids: ['doc1', 'doc2'], has_full_access: false }
```

## RoleClient

RBAC action checks. Mirrors the Python SDK.

```typescript
const roles = new RoleClient(
  'http://localhost:9003', 'my-service', 'sk_my_service_key',
)
```

**registerActions(actions)** -- register at startup (service key).

```typescript
await roles.registerActions([
  { action: 'notes:create', description: 'Create notes' },
  { action: 'notes:export', description: 'Export notes' },
])
```

**checkAction(token, action, workspaceId)** -- check single action.

```typescript
const allowed = await roles.checkAction(token, 'notes:export', workspaceId)
```

**getUserActions(token, workspaceId)** -- list permitted actions.

```typescript
const actions = await roles.getUserActions(token, workspaceId)
// ['notes:create', 'notes:export']
```

## Express example

```typescript
import express from 'express'
import { verifyToken, payloadToUser, PermissionClient } from '@sentinel-auth/js/server'

const app = express()
const permissions = new PermissionClient('http://localhost:9003', 'my-service', process.env.SERVICE_KEY)

async function authenticate(req, res, next) {
  const token = req.headers.authorization?.replace('Bearer ', '')
  if (!token) return res.status(401).json({ error: 'Unauthorized' })
  try {
    req.user = payloadToUser(await verifyToken(token, {
      jwksUrl: 'http://localhost:9003/.well-known/jwks.json',
    }))
    req.token = token
    next()
  } catch {
    res.status(401).json({ error: 'Invalid token' })
  }
}

app.get('/api/documents/:id', authenticate, async (req, res) => {
  const allowed = await permissions.can(req.token, 'document', req.params.id, 'view')
  if (!allowed) return res.status(403).json({ error: 'Forbidden' })
  res.json(await getDocument(req.params.id))
})
```
