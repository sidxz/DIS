# Tutorial: Next.js Frontend

This tutorial shows how to build the **Team Notes** frontend using Next.js App Router and `@sentinel-auth/nextjs`. It covers the same app as the [main tutorial](tutorial.md) (Steps 1–9 for the FastAPI backend are identical) but replaces the Vite + React Router frontend with Next.js.

!!! tip "Backend first"
    Complete [Steps 1–9 of the main tutorial](tutorial.md) before starting here. This page only covers the Next.js frontend.

## Prerequisites

- Sentinel running locally with the backend from the main tutorial
- Node.js 18+
- Familiarity with Next.js App Router

## What's Different from React + Vite?

| Concern | React + Vite | Next.js |
|---------|-------------|---------|
| Auth enforcement | `AuthGuard` component | Edge Middleware (server-side) |
| User in server code | N/A | `getUser()` / `requireUser()` from headers |
| Route handlers | Separate FastAPI backend | Can use Next.js Route Handlers alongside FastAPI |
| Client components | Everything is client | Explicit `'use client'` where needed |
| Imports | `@sentinel-auth/react` | `@sentinel-auth/nextjs` (re-exports with `'use client'`) |

---

## Step 1: Create the Next.js App

```bash
npx create-next-app@latest team-notes-nextjs --typescript --tailwind --app --src-dir
cd team-notes-nextjs
npm install @sentinel-auth/js @sentinel-auth/nextjs @tanstack/react-query
```

Add the Sentinel URL to `.env.local`:

```dotenv
NEXT_PUBLIC_SENTINEL_URL=http://localhost:9003
```

## Step 2: Edge Middleware

Create `middleware.ts` in the project root. This verifies JWTs at the edge before any page or API route runs:

```typescript
// middleware.ts
import { createSentinelMiddleware } from '@sentinel-auth/nextjs/middleware'

export default createSentinelMiddleware({
  jwksUrl: process.env.SENTINEL_JWKS_URL || 'http://localhost:9003/.well-known/jwks.json',
  publicPaths: ['/login', '/auth/callback'],
})

export const config = {
  matcher: ['/((?!_next|favicon.ico).*)'],
}
```

This replaces `AuthGuard` — unauthenticated requests to page routes are redirected to `/login`, and API routes get a `401` JSON response. No client-side loading state needed for route protection.

## Step 3: Auth Provider Layout

The auth provider is a Client Component that wraps all pages. The client instance is created once and shared:

```tsx
// src/lib/sentinel.ts
import { SentinelAuth } from '@sentinel-auth/js'

const SENTINEL_URL = process.env.NEXT_PUBLIC_SENTINEL_URL || 'http://localhost:9003'

export const sentinelClient = new SentinelAuth({
  sentinelUrl: SENTINEL_URL,
})

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  return sentinelClient.fetchJson<T>(path, options)
}
```

```tsx
// src/app/providers.tsx
'use client'

import { SentinelAuthProvider } from '@sentinel-auth/nextjs'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'
import { sentinelClient } from '@/lib/sentinel'

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1 } } }),
  )

  return (
    <SentinelAuthProvider client={sentinelClient}>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </SentinelAuthProvider>
  )
}
```

```tsx
// src/app/layout.tsx
import { Providers } from './providers'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
```

## Step 4: Login Page

The login page is a public path (skipped by middleware), so it renders without auth:

```tsx
// src/app/login/page.tsx
'use client'

import { useAuth } from '@sentinel-auth/nextjs'

export default function LoginPage() {
  const { login } = useAuth()

  return (
    <div className="flex h-screen items-center justify-center">
      <button
        onClick={() => login('google')}
        className="rounded-lg bg-white px-6 py-3 text-sm font-medium text-gray-800 shadow hover:bg-gray-50"
      >
        Sign in with Google
      </button>
    </div>
  )
}
```

## Step 5: OAuth Callback

Use the SDK's `AuthCallback` component. Since `/auth/callback` is a public path, the middleware won't redirect it:

```tsx
// src/app/auth/callback/page.tsx
'use client'

import { useRouter } from 'next/navigation'
import { AuthCallback } from '@sentinel-auth/nextjs'

export default function AuthCallbackPage() {
  const router = useRouter()

  return (
    <AuthCallback
      onSuccess={() => router.replace('/notes')}
      loadingComponent={
        <div className="flex h-screen items-center justify-center">
          <p className="text-sm text-gray-500">Signing you in...</p>
        </div>
      }
      errorComponent={(error) => (
        <div className="flex h-screen items-center justify-center">
          <div className="text-center">
            <p className="mb-4 text-sm text-red-500">{error.message}</p>
            <a href="/login" className="text-sm underline">Back to login</a>
          </div>
        </div>
      )}
      workspaceSelector={({ workspaces, onSelect, isLoading }) => (
        <div className="flex h-screen items-center justify-center">
          <div className="w-full max-w-sm space-y-2">
            <h2 className="text-center text-lg font-semibold">Select Workspace</h2>
            {workspaces.map((ws) => (
              <button
                key={ws.id}
                onClick={() => onSelect(ws.id)}
                disabled={isLoading}
                className="w-full rounded-lg border p-4 text-left hover:bg-gray-50 disabled:opacity-50"
              >
                <div className="font-medium">{ws.name}</div>
                <div className="text-xs text-gray-500">{ws.slug} — {ws.role}</div>
              </button>
            ))}
          </div>
        </div>
      )}
    />
  )
}
```

## Step 6: Server Component — User Context

Behind the middleware, use `getUser()` to read the authenticated user in Server Components:

```tsx
// src/app/notes/layout.tsx
import { getUser } from '@sentinel-auth/nextjs/server'
import { LogoutButton } from './logout-button'

export default async function NotesLayout({ children }: { children: React.ReactNode }) {
  const user = await getUser()

  return (
    <div>
      <nav className="flex items-center justify-between border-b px-6 py-3">
        <span className="text-sm">
          {user?.name} — {user?.workspaceSlug} ({user?.workspaceRole})
        </span>
        <LogoutButton />
      </nav>
      {children}
    </div>
  )
}
```

```tsx
// src/app/notes/logout-button.tsx
'use client'

import { useAuth } from '@sentinel-auth/nextjs'
import { useRouter } from 'next/navigation'

export function LogoutButton() {
  const { logout } = useAuth()
  const router = useRouter()

  return (
    <button
      onClick={() => { logout(); router.replace('/login') }}
      className="text-sm text-gray-500 hover:text-gray-800"
    >
      Logout
    </button>
  )
}
```

## Step 7: Client Component — Fetch Notes

Use `fetchJson` via the `apiFetch` wrapper with React Query:

```tsx
// src/app/notes/page.tsx
'use client'

import { useQuery } from '@tanstack/react-query'
import { useHasRole } from '@sentinel-auth/nextjs'
import { apiFetch } from '@/lib/sentinel'

interface Note {
  id: string
  title: string
  content: string
}

export default function NotesPage() {
  const canCreate = useHasRole('editor')
  const { data: notes } = useQuery({
    queryKey: ['notes'],
    queryFn: () => apiFetch<Note[]>('/api/notes'),
  })

  return (
    <div className="mx-auto max-w-2xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold">Notes</h1>
        {canCreate && <button className="rounded bg-blue-600 px-4 py-2 text-sm text-white">New Note</button>}
      </div>
      <ul className="space-y-2">
        {notes?.map((note) => (
          <li key={note.id} className="rounded border p-4">
            <div className="font-medium">{note.title}</div>
            <div className="text-sm text-gray-500">{note.content}</div>
          </li>
        ))}
      </ul>
    </div>
  )
}
```

## Step 8: Route Handler with `withAuth`

You can also add Next.js Route Handlers that proxy or augment your FastAPI backend. Use `withAuth` to enforce authentication:

```typescript
// src/app/api/me/route.ts
import { withAuth } from '@sentinel-auth/nextjs/server'

export const GET = withAuth(async (req, user) => {
  return Response.json({
    userId: user.userId,
    email: user.email,
    workspace: user.workspaceSlug,
    role: user.workspaceRole,
  })
})
```

## Step 9: Configure and Run

### Register the client app

In the Sentinel admin panel, go to **Client Apps** and add:

- **Name**: `team-notes-nextjs`
- **Redirect URIs**: `http://localhost:3000/auth/callback`

### Environment

```dotenv
# .env.local
NEXT_PUBLIC_SENTINEL_URL=http://localhost:9003
SENTINEL_JWKS_URL=http://localhost:9003/.well-known/jwks.json
```

### Start

```bash
# Terminal 1: Sentinel + demo backend (from main tutorial)
make infra && make start
cd demo/backend && uv run python -m src.main

# Terminal 2: Next.js frontend
cd team-notes-nextjs && npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and sign in with Google.

## Summary

| What | How | SDK API |
|------|-----|---------|
| Route protection | Edge Middleware | `createSentinelMiddleware()` |
| User in Server Components | Read headers set by middleware | `getUser()`, `requireUser()` |
| User in Client Components | React context | `useUser()`, `useAuth()` |
| OAuth callback | SDK component | `AuthCallback` with render props |
| Authenticated fetch | Auto Bearer + JSON parsing | `sentinelClient.fetchJson()` |
| Role checks | Hook | `useHasRole("editor")` |
| Route Handlers | HOC wrapper | `withAuth()` |

## Next Steps

- [Main Tutorial](tutorial.md) — FastAPI backend setup (Steps 1–9)
- [Next.js SDK Reference](../js-sdk/nextjs.md) — full middleware, server, and client API docs
- [React Integration](../js-sdk/react.md) — hooks and components reference
- [Auth Client](../js-sdk/auth-client.md) — `SentinelAuth` class reference
