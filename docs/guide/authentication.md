# Authentication

## Supported IdPs

Sentinel proxies authentication from three identity providers. Provider registration is conditional -- if the environment variables are not set, the provider is not available.

| Provider | Protocol | PKCE | Scopes |
|---|---|---|---|
| Google | OIDC | S256 | `openid email profile` |
| GitHub | OAuth2 | None | `user:email` |
| Microsoft Entra ID | OIDC | S256 | `openid email profile` |

**Google** -- Standard OIDC with automatic discovery. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

**GitHub** -- OAuth2 only (not OIDC, no PKCE). User info fetched via GitHub API. If the primary email is not in the profile response, it is fetched from `GET /user/emails`. Set `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET`.

**Entra ID** -- OIDC with tenant-specific discovery. Set `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET`, and `ENTRA_TENANT_ID`.

See [How Sentinel Works](how-it-works.md) for the full login flows in both AuthZ and Proxy modes.

## Token Types

| Token | Audience | TTL | Purpose |
|---|---|---|---|
| Access | `sentinel:access` | 15 min | Identity + authorization in Proxy mode. Carries user info, workspace context, and group memberships. |
| Refresh | `sentinel:refresh` | 7 days | Silent renewal of access tokens. Supports rotation with reuse detection. |
| Admin | `sentinel:admin` | 60 min | Admin panel sessions. Carries `admin: true` flag. |
| Authz | `sentinel:authz` | 5 min | Authorization-only in AuthZ mode. Carries workspace role and RBAC actions. No identity -- identity comes from the IdP token. |

All tokens are RS256-signed JWTs. The algorithm is hardcoded at both encode and decode time to prevent algorithm substitution attacks. Audience validation is mandatory on every decode call.

## JWT Claims

### Access Token Claims

| Claim | Type | Example | Description |
|---|---|---|---|
| `iss` | string | `https://auth.example.com` | Issuer. Sentinel's `BASE_URL`. |
| `sub` | string (UUID) | `"d4f5a..."` | User ID. |
| `jti` | string (UUID) | `"8b3c1..."` | Unique token ID. Enables per-token revocation via Redis denylist. |
| `aud` | string | `"sentinel:access"` | Audience. Always `sentinel:access`. |
| `email` | string | `"alice@co.com"` | User's email address. |
| `name` | string | `"Alice Chen"` | User's display name. |
| `wid` | string (UUID) | `"a1b2c..."` | Workspace ID. |
| `wslug` | string | `"acme"` | Workspace slug. |
| `wrole` | string | `"editor"` | Workspace role: `owner`, `admin`, `editor`, or `viewer`. |
| `groups` | string[] | `["uuid1", "uuid2"]` | Group IDs the user belongs to in this workspace. |
| `iat` | number | `1709827200` | Issued-at timestamp (UTC). |
| `exp` | number | `1709828100` | Expiration timestamp (UTC). `iat` + 15 minutes. |
| `type` | string | `"access"` | Token type discriminator. |

### Authz Token Claims

| Claim | Type | Example | Description |
|---|---|---|---|
| `iss` | string | `https://auth.example.com` | Issuer. Sentinel's `BASE_URL`. |
| `sub` | string (UUID) | `"d4f5a..."` | User ID. |
| `jti` | string (UUID) | `"8b3c1..."` | Unique token ID. Enables revocation via denylist. |
| `aud` | string | `"sentinel:authz"` | Audience. Always `sentinel:authz`. |
| `idp_sub` | string | `"104523..."` | IdP subject identifier. Binds this token to a specific IdP identity. The backend validates that the IdP token's `sub` matches this value. |
| `svc` | string | `"docu-store"` | Service name. Binds the token to a specific service, preventing cross-service replay. |
| `wid` | string (UUID) | `"a1b2c..."` | Workspace ID. |
| `wslug` | string | `"acme"` | Workspace slug. |
| `wrole` | string | `"editor"` | Workspace role. |
| `actions` | string[] | `["docs:read", "docs:write"]` | RBAC actions granted to this user for this service in this workspace. |
| `iat` | number | `1709827200` | Issued-at timestamp (UTC). |
| `exp` | number | `1709827500` | Expiration timestamp (UTC). `iat` + 5 minutes. |
| `type` | string | `"authz"` | Token type discriminator. |

### Refresh Token Claims

| Claim | Type | Example | Description |
|---|---|---|---|
| `iss` | string | `https://auth.example.com` | Issuer. |
| `sub` | string (UUID) | `"d4f5a..."` | User ID. |
| `jti` | string (UUID) | `"8b3c1..."` | Unique token ID. |
| `aud` | string | `"sentinel:refresh"` | Audience. Always `sentinel:refresh`. |
| `fid` | string (UUID) | `"f7e8d..."` | Family ID. Groups refresh tokens into rotation families for reuse detection. |
| `iat` | number | `1709827200` | Issued-at timestamp (UTC). |
| `exp` | number | `1710432000` | Expiration timestamp (UTC). `iat` + 7 days. |
| `type` | string | `"refresh"` | Token type discriminator. |

### Admin Token Claims

| Claim | Type | Example | Description |
|---|---|---|---|
| `iss` | string | `https://auth.example.com` | Issuer. |
| `sub` | string (UUID) | `"d4f5a..."` | User ID. |
| `jti` | string (UUID) | `"8b3c1..."` | Unique token ID. |
| `aud` | string | `"sentinel:admin"` | Audience. Always `sentinel:admin`. |
| `email` | string | `"alice@co.com"` | Admin user's email. |
| `name` | string | `"Alice Chen"` | Admin user's display name. |
| `admin` | boolean | `true` | Always `true`. |
| `iat` | number | `1709827200` | Issued-at timestamp (UTC). |
| `exp` | number | `1709830800` | Expiration timestamp (UTC). `iat` + 60 minutes. |
| `type` | string | `"admin_access"` | Token type discriminator. |

## Token Lifecycle

### Refresh Rotation with Reuse Detection

Refresh tokens use a family-based rotation scheme:

1. On login, a refresh token is issued with a unique `fid` (family ID).
2. When the client refreshes, the old refresh token is consumed and a new one is issued with the same `fid`.
3. If a consumed refresh token is presented again (reuse), the entire family is invalidated -- all tokens sharing that `fid` are denied.

This detects token theft: if an attacker steals a refresh token and uses it, either the attacker or the legitimate user will trigger reuse detection, invalidating the family.

### Revocation

Individual tokens are revoked by adding their `jti` to a Redis denylist. The denylist entry TTL matches the token's remaining lifetime, so entries self-clean. Every token validation checks the denylist before accepting the token.

Logout revokes both the access token and the refresh token's entire family.
