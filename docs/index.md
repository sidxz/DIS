---
title: Sentinel Auth
---

# Sentinel

Sentinel is an authentication proxy and authorization microservice.

- **Proxies IdP authentication** -- users sign in with Google, GitHub, or EntraID. Sentinel validates their IdP token and issues an authorization JWT.
- **Manages workspaces** -- multi-tenant workspace membership, groups, and role assignments.
- **Three-tier authorization** -- workspace roles (JWT claims), custom RBAC roles (database), and Zanzibar-style entity ACLs (per-resource).

## How it works

Your app authenticates users directly with your identity provider. Sentinel does not handle login -- it handles what comes after. Your frontend sends the IdP token to Sentinel, gets back an authz token, and your backend validates both.

## Quick integration

Install the SDK and protect a route in four lines:

```python
from sentinel_auth import Sentinel

sentinel = Sentinel(
    auth_url="https://sentinel.example.com",
    service_name="my-app",
    service_key="sk_...",
)

# FastAPI dependency -- validates IdP token + authz token, returns user
user = sentinel.require_user

@app.get("/projects")
async def list_projects(user=Depends(user)):
    return await get_projects(user.workspace_id)
```

```bash
pip install sentinel-auth-sdk
```

## Next steps

- [Quickstart](getting-started/quickstart.md) -- run Sentinel and connect your first app
- [How It Works](guide/how-it-works.md) -- architecture and auth flow
- [Python SDK](sdk/index.md) -- middleware, dependencies, permissions, roles
- [JS/TS SDK](js-sdk/index.md) -- browser, React, and Next.js packages
