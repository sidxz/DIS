# Next.js Integration

The `@sentinel-auth/nextjs` package provides Edge Middleware for JWT validation, server helpers for Server Components and Route Handlers, and client-side re-exports from `@sentinel-auth/react`.

## Edge Middleware

Protect all routes with JWT verification at the edge. The middleware verifies tokens via JWKS and forwards user info to downstream components via request headers.

### Setup

Create `middleware.ts` in your project root:

```typescript
import { createSentinelMiddleware } from '@sentinel-auth/nextjs/middleware'

export default createSentinelMiddleware({
  jwksUrl: 'http://localhost:9003/.well-known/jwks.json',
  publicPaths: ['/login', '/auth/callback'],
})

export const config = {
  matcher: ['/((?!_next|favicon.ico).*)'],
}
```

### Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `jwksUrl` | `string` | *required* | URL to the Sentinel JWKS endpoint |
| `publicPaths` | `string[]` | `[]` | Paths that skip authentication |
| `loginPath` | `string` | `"/login"` | Redirect target for unauthenticated page requests |
| `audience` | `string` | `"sentinel:access"` | Expected JWT audience |
| `allowedWorkspaces` | `string[]` | — | Optional workspace ID allowlist |

### Behavior

1. **Public paths** are passed through without authentication
2. Token is extracted from the `Authorization: Bearer` header or the `sentinel_access_token` cookie
3. Token is verified against the JWKS endpoint using `jose`
4. On success, user info is forwarded via `x-sentinel-*` response headers
5. On failure:
    - **API routes** (`/api/*`) receive a `401 Unauthorized` JSON response
    - **Page routes** are redirected to `loginPath`

### Headers Set

The middleware sets these headers on successful verification, readable in Server Components and Route Handlers:

| Header | Description |
|--------|-------------|
| `x-sentinel-user-id` | User ID |
| `x-sentinel-email` | Email address |
| `x-sentinel-name` | Display name |
| `x-sentinel-workspace-id` | Workspace ID |
| `x-sentinel-workspace-slug` | Workspace slug |
| `x-sentinel-workspace-role` | Workspace role |

## Server Helpers

Read user information set by the middleware in Server Components and Route Handlers.

### `getUser`

Returns the current user or `null` if not authenticated.

```typescript
import { getUser } from '@sentinel-auth/nextjs/server'

export default async function DashboardPage() {
  const user = await getUser()
  if (!user) return <p>Not authenticated</p>
  return <p>Welcome, {user.name}!</p>
}
```

### `requireUser`

Returns the current user or throws an error (for use with error boundaries or try/catch).

```typescript
import { requireUser } from '@sentinel-auth/nextjs/server'

export default async function ProfilePage() {
  const user = await requireUser()
  return <p>{user.email}</p>
}
```

### `getToken`

Get the raw JWT from the `Authorization` header.

```typescript
import { getToken } from '@sentinel-auth/nextjs/server'

export default async function ApiPage() {
  const token = await getToken()
  // Use token for downstream API calls
}
```

### `withAuth`

HOC for Route Handlers that require authentication. Extracts the user and passes it to your handler.

```typescript
import { withAuth } from '@sentinel-auth/nextjs/server'

export const GET = withAuth(async (req, user) => {
  return Response.json({ userId: user.userId, workspace: user.workspaceSlug })
})
```

## Client-Side Components

The default import re-exports everything from `@sentinel-auth/react` with `'use client'`, so you can use all React hooks and components in Next.js Client Components:

```tsx
'use client'

import { useAuth, useUser, AuthGuard, AuthCallback } from '@sentinel-auth/nextjs'
```

See the [React Integration](react.md) docs for full details on these exports.

## Full Example

=== "middleware.ts"

    ```typescript
    import { createSentinelMiddleware } from '@sentinel-auth/nextjs/middleware'

    export default createSentinelMiddleware({
      jwksUrl: process.env.SENTINEL_JWKS_URL!,
      publicPaths: ['/login', '/auth/callback'],
    })

    export const config = {
      matcher: ['/((?!_next|favicon.ico).*)'],
    }
    ```

=== "app/layout.tsx (Server)"

    ```tsx
    import { getUser } from '@sentinel-auth/nextjs/server'

    export default async function RootLayout({ children }) {
      const user = await getUser()
      return (
        <html>
          <body>
            <nav>{user ? `Hi, ${user.name}` : 'Not signed in'}</nav>
            {children}
          </body>
        </html>
      )
    }
    ```

=== "app/login/page.tsx (Client)"

    ```tsx
    'use client'

    import { SentinelAuthProvider, useAuth } from '@sentinel-auth/nextjs'

    function LoginButton() {
      const { login } = useAuth()
      return <button onClick={() => login('google')}>Sign in</button>
    }

    export default function LoginPage() {
      return (
        <SentinelAuthProvider config={{ sentinelUrl: process.env.NEXT_PUBLIC_SENTINEL_URL! }}>
          <LoginButton />
        </SentinelAuthProvider>
      )
    }
    ```

=== "app/api/notes/route.ts"

    ```typescript
    import { withAuth } from '@sentinel-auth/nextjs/server'

    export const GET = withAuth(async (req, user) => {
      const notes = await db.notes.findMany({
        where: { workspaceId: user.workspaceId },
      })
      return Response.json(notes)
    })
    ```

## Next Steps

- [React Integration](react.md) -- hooks, components, and provider
- [Server Utilities](server.md) -- JWT verification and permission checks
- [Auth Client](auth-client.md) -- underlying browser auth client
