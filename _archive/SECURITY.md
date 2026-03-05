# Security — Daikon Identity Service

## Implementation Status

### Transport & Session
- [x] SessionMiddleware secret loaded from `SESSION_SECRET_KEY` env var (no hardcoded default)
- [x] CORS restricted to explicit origins, methods, and headers
- [x] Security headers on all responses (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy)
- [x] HSTS enabled when `COOKIE_SECURE=true` (production)
- [x] TrustedHostMiddleware when `ALLOWED_HOSTS` is set
- [ ] TLS termination via reverse proxy (Caddy/Traefik) — deployment config

### Authentication
- [x] JWT RS256 signing with `jti` claim for revocation
- [x] `get_current_user` dependency on all user/workspace/group routes (replaces 401 stubs)
- [x] Role-based authorization checks (admin/owner required for mutations)
- [x] Refresh token rotation with one-time use (Redis-backed)
- [x] Reuse detection — consuming an already-used refresh token revokes entire token family
- [x] Access token revocation via `jti` denylist in Redis
- [x] `POST /auth/refresh` implemented
- [x] `POST /auth/logout` implemented (blacklists access token)

### Service-to-Service
- [x] `X-Service-Key` header validated via `require_service_key` dependency
- [x] Dev mode: empty `SERVICE_API_KEYS` = no enforcement
- [x] Production: all `/permissions/*` routes require valid service key
- [x] Dual auth on `/check`, `/accessible`, `/share` (service key + user JWT)
- [x] Service-only auth on `/register`, `/visibility`, revoke, GET ACL
- [x] SDK `PermissionClient` supports `service_key` parameter

### Cookie Security
- [x] Admin cookie: `HttpOnly`, `SameSite=Strict`, 1-hour max-age
- [x] `Secure` flag controlled by `COOKIE_SECURE` config (True in production)

### Rate Limiting
- [x] slowapi with in-memory backend (swap to Redis for multi-worker)
- [x] Auth login/callback: 10/minute per IP
- [x] Admin login/callback: 5/minute per IP
- [x] Token refresh: 10/minute per IP

### OAuth Hardening
- [x] PKCE S256 on Google and EntraID (Authlib native support)
- [x] GitHub: no PKCE (not supported by GitHub), state parameter via SessionMiddleware
- [x] Authlib handles state parameter validation internally

### Input Validation & Error Handling
- [x] CSV upload size limit: 5 MB
- [x] No tracebacks in error responses (server-side logging only)
- [x] Pydantic validation on all request schemas

### Audit Logging
- [x] User login events logged to `activity_logs`
- [x] Admin login events logged to `activity_logs`
- [x] Includes: user_id, provider, IP address

---

## Production Checklist

Before deploying to production:

1. **Set all required env vars:**
   ```
   SESSION_SECRET_KEY=<random 32-byte string>
   SERVICE_API_KEYS=<key1>,<key2>
   COOKIE_SECURE=true
   ALLOWED_HOSTS=your-domain.com
   CORS_ORIGINS=https://your-frontend.com
   ```

2. **Rotate any credentials that were ever in git history**

3. **Deploy behind a TLS-terminating reverse proxy** (Caddy recommended)

4. **For multi-worker deployments:** configure slowapi to use Redis backend

5. **Generate strong service API keys:**
   ```
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

---

## Architecture: Auth Tiers

| Caller | Auth method | Endpoints |
|--------|-------------|-----------|
| End users (browser) | JWT in `Authorization: Bearer` | `/auth/*`, `/users/*`, `/workspaces/*` |
| Service backends | `X-Service-Key` + user JWT | `/permissions/check`, `/permissions/accessible`, `/permissions/{id}/share` |
| Service backends | `X-Service-Key` only | `/permissions/register`, visibility, revoke, GET ACL |
| Admin panel | JWT in `admin_token` cookie | `/admin/*` |
