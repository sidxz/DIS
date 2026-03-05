---
title: Daikon Identity Service
description: Authentication, workspace management, and Zanzibar-style permissions for Python microservices
---

# Daikon Identity Service

**A production-ready identity microservice for Python applications.** Daikon handles OAuth2/OIDC authentication, multi-tenant workspace management, and fine-grained Zanzibar-style permissions so you can focus on your application logic.

Built with **FastAPI**, **SQLAlchemy 2.0** (async), **PostgreSQL 16**, **Redis 7**, and **Authlib**.

---

## Key Features

<div class="grid cards" markdown>

-   :material-shield-lock:{ .lg .middle } **OAuth2 / OIDC Authentication**

    ---

    Sign in with Google, GitHub, and Microsoft EntraID out of the box. PKCE S256 on supported providers, RS256 JWT tokens with refresh rotation and reuse detection.

    [:octicons-arrow-right-24: Authentication guide](guide/authentication.md)

-   :material-office-building:{ .lg .middle } **Multi-Tenant Workspaces**

    ---

    Isolate users, groups, and resources by workspace. Role-based access control at the workspace level with `owner`, `admin`, `member`, and `viewer` roles embedded in every JWT.

    [:octicons-arrow-right-24: Workspace management](guide/workspaces.md)

-   :material-lock-check:{ .lg .middle } **Zanzibar-Style Permissions**

    ---

    Generic resource permissions with `service_name`, `resource_type`, and `resource_id`. Check access, list accessible resources, and share via ACLs -- all through a simple API.

    [:octicons-arrow-right-24: Permissions model](guide/permissions.md)

-   :material-language-python:{ .lg .middle } **Python SDK**

    ---

    Install `daikon-identity-sdk` and integrate in minutes. The SDK handles JWT validation, permission checks, and resource registration with a clean, typed Python API.

    [:octicons-arrow-right-24: SDK reference](sdk/index.md)

-   :material-key-chain:{ .lg .middle } **Service-to-Service Auth**

    ---

    Secure inter-service communication with API keys via the `X-Service-Key` header. Three auth tiers -- user JWT, dual (service key + JWT), and service-key-only -- for flexible access control.

    [:octicons-arrow-right-24: Security model](security.md)

-   :material-view-dashboard:{ .lg .middle } **Admin Panel**

    ---

    Built-in admin interface for managing users, workspaces, groups, and permissions. Activity logging, CSV import/export, and a dashboard for operational visibility.

    [:octicons-arrow-right-24: Admin guide](guide/admin.md)

</div>

---

## Get Started

Choose your path based on what you need to do:

<div class="grid cards" markdown>

-   :material-puzzle:{ .lg .middle } **I want to integrate the SDK**

    ---

    You have a Python service and want to add authentication and permission checks using the Daikon Identity SDK.

    1. Install the SDK: `pip install daikon-identity-sdk`
    2. Configure your service key and identity service URL
    3. Use `PermissionClient` to check and manage permissions
    4. Validate JWTs to extract user and workspace context

    [:octicons-arrow-right-24: SDK quickstart](sdk/index.md)

-   :material-server:{ .lg .middle } **I want to run the service**

    ---

    You want to deploy the Daikon Identity Service as your authentication and authorization backend.

    1. Clone the repository and configure `.env`
    2. Set up PostgreSQL 16 and Redis 7
    3. Generate RS256 key pair for JWT signing
    4. Register OAuth2 credentials with your identity providers
    5. Run with `uv run uvicorn` or deploy with Docker

    [:octicons-arrow-right-24: Deployment guide](getting-started/index.md)

</div>

---

## Architecture at a Glance

Daikon Identity Service sits between your frontend applications and your backend microservices:

```
Frontend App          Daikon Identity Service          Your Microservices
-----------           -----------------------          ------------------
                      +---------------------+
  Login via    -----> | OAuth2/OIDC (Authlib)|
  Google/GitHub/      | Session + PKCE       |
  EntraID             +---------------------+
                              |
                      +---------------------+
  JWT in Auth  <----- | JWT Issuance (RS256) |
  header              | Access + Refresh     |
                      +---------------------+
                              |
  API calls    -----> +---------------------+          +------------------+
  with Bearer         | User / Workspace /  | -------> | Permission checks|
  token               | Group Management    |          | via SDK or API   |
                      +---------------------+          +------------------+
                              |
                      +---------------------+
                      | Zanzibar Permissions |
                      | register / check /   |
                      | share / accessible   |
                      +---------------------+
```

**No local passwords.** Users always authenticate through external identity providers. Daikon manages their identity, workspace membership, group assignments, and fine-grained resource permissions.

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Web framework** | FastAPI | Async HTTP API with OpenAPI docs |
| **ORM** | SQLAlchemy 2.0 (async) | Database models and queries |
| **Database** | PostgreSQL 16 | Persistent storage for users, workspaces, groups, permissions |
| **Cache / tokens** | Redis 7 | Refresh token families, access token denylist, rate limiting |
| **OAuth2 / OIDC** | Authlib | Provider integration (Google, GitHub, EntraID) |
| **JWT** | PyJWT + RS256 | Stateless access tokens with workspace context |
| **Package manager** | uv workspaces | Monorepo with `service/` and `sdk/` packages |
