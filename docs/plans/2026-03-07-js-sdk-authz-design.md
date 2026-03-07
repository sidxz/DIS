# JS SDK AuthZ Mode Support — Design

## Goal

Add authz mode support to `@sentinel-auth/js`, `@sentinel-auth/react`, and `@sentinel-auth/nextjs` so client apps can use the dual-token architecture (IdP token + Sentinel authz token) with the same developer experience as proxy mode.

## Architecture

```
Browser                        Client Backend            Sentinel
  │                                │                        │
  │  1. IdP Sign-In (Google)       │                        │
  │  ──────► Google ──────►        │                        │
  │  ◄── IdP token (1hr)           │                        │
  │                                │                        │
  │  2. POST /auth/resolve         │                        │
  │  { idp_token, provider }  ───► │  POST /authz/resolve   │
  │                                │  + X-Service-Key  ───► │
  │                                │  ◄── authz_token       │
  │  ◄── { authz_token, user,     │                        │
  │       workspaces }             │                        │
  │                                │                        │
  │  3. Every API call             │                        │
  │  Authorization: Bearer <idp>   │                        │
  │  X-Authz-Token: <authz>  ───► │  AuthzMiddleware       │
  │                                │  validates both        │
```

## Package Changes

### `@sentinel-auth/js` — `SentinelAuthz`

**Config:** Single `backendUrl` — derives `/auth/resolve`.

```ts
interface SentinelAuthzConfig {
  backendUrl: string
  storage?: AuthzTokenStore
  autoRefresh?: boolean        // default: true
  refreshBuffer?: number       // seconds before expiry (default: 30)
}
```

**Storage keys:** `sentinel_idp_token`, `sentinel_authz_token`, `sentinel_idp_provider`, `sentinel_workspace_id`.

**API:**
- `resolve(idpToken, provider)` → workspace list or authz context
- `selectWorkspace(idpToken, provider, workspaceId)` → stores both tokens
- `getUser()` → `SentinelUser | null`
- `getHeaders()` → `{ Authorization, X-Authz-Token }`
- `fetch()` / `fetchJson()` → auto-headers, 401 retry
- `logout()`, `onAuthStateChange()`, `destroy()`

**Refresh:** Schedules re-resolve before authz token expiry using stored IdP token + provider + workspace. Logs out if IdP token has also expired.

### `@sentinel-auth/react` — `AuthzProvider`

- `AuthzProvider` — wraps `SentinelAuthz`, exposes context with `resolve`, `selectWorkspace`, `user`, `fetch`, `fetchJson`
- `useAuthz()` — access authz context
- `AuthzGuard` — renders children if authenticated, fallback if not

### `@sentinel-auth/nextjs` — Authz Middleware

```ts
createSentinelAuthzMiddleware({
  sentinelUrl: string,       // derives /.well-known/jwks.json
  idpJwksUrl: string,        // e.g. Google's JWKS
  publicPaths?: string[],
})
```

Validates both tokens at Edge, checks idp_sub binding, sets x-sentinel-* headers.

### Backend Convention

SDK expects `POST {backendUrl}/auth/resolve` — a thin proxy using `sentinel.authz.resolve()`.

## Files

| Package | New Files |
|---------|-----------|
| `sdks/js/src/` | `authz-client.ts`, `authz-types.ts`, `authz-storage.ts` |
| `sdks/react/src/` | `authz-provider.tsx`, `authz-hooks.ts`, `authz-guard.tsx` |
| `sdks/nextjs/src/` | `authz-middleware.ts` |
| `demo-authz/backend/` | Add `/auth/resolve` proxy endpoint |
| `demo-authz/frontend/` | React app with Google Sign-In + `AuthzProvider` |
