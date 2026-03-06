# Tutorial: Build Your First App

This tutorial walks through building a **Team Notes** app — a FastAPI backend with a React frontend — that uses the Sentinel Auth SDK for authentication, workspace isolation, role enforcement, and entity-level permissions.

The complete source code is in the `demo/` directory of this repository.

## Prerequisites

- Identity service running locally ([Installation](../getting-started/installation.md), [Quickstart](../getting-started/quickstart.md))
- Google OAuth credentials configured
- RSA key pair at `keys/private.pem` / `keys/public.pem`
- Python 3.12+ and Node.js 18+

## What You'll Build

A note-taking app that demonstrates all three authorization tiers:

| Tier | Feature | SDK API |
|------|---------|---------|
| **Workspace Roles** | Editors create notes, admins delete | `require_role("editor")` |
| **Custom RBAC** | Export requires a registered action | `require_action(client, "notes:export")` |
| **Entity ACLs** | View/edit individual notes | `PermissionClient.can()` |

---

## Step 1: Create the Backend

Create a new FastAPI project that depends on the SDK:

```toml
# demo/backend/pyproject.toml
[project]
name = "demo-team-notes"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "pydantic-settings>=2.7.0",
    "sentinel-auth-sdk",
]
```

Install:

```bash
cd demo/backend
uv sync
```

!!! tip "Editable installs for SDK development"
    If you're working on the SDK itself and want changes reflected immediately, add a `[tool.uv.sources]` section pointing to your local SDK checkout:

    ```toml
    [tool.uv.sources]
    sentinel-auth-sdk = { path = "../../sdk", editable = true }
    ```

## Step 2: Add JWT Middleware

The `JWTAuthMiddleware` validates Bearer tokens on every request and populates `request.state.user` with an `AuthenticatedUser` object.

=== "JWKS URL (recommended)"

    Use the JWKS endpoint for automatic key discovery and rotation — no need to distribute PEM files:

    ```python
    # src/main.py
    from fastapi import FastAPI
    from sentinel_auth.middleware import JWTAuthMiddleware

    app = FastAPI(title="Team Notes")

    app.add_middleware(
        JWTAuthMiddleware,
        jwks_url="http://localhost:9003/.well-known/jwks.json",
        exclude_paths=["/health", "/docs", "/openapi.json", "/redoc"],
    )
    ```

=== "PEM file"

    Load the public key directly from the filesystem:

    ```python
    # src/main.py
    from fastapi import FastAPI
    from sentinel_auth.middleware import JWTAuthMiddleware
    from src.config import settings

    PUBLIC_KEY = settings.public_key_path.read_text()

    app = FastAPI(title="Team Notes")

    app.add_middleware(
        JWTAuthMiddleware,
        public_key=PUBLIC_KEY,
        exclude_paths=["/health", "/docs", "/openapi.json", "/redoc"],
    )
    ```

After this, every request (except excluded paths) must include a valid `Authorization: Bearer <token>` header.

!!! tip "Restricting to specific workspaces"
    If your app should only be accessible to members of certain workspaces, add the `allowed_workspaces` parameter:

    ```python
    app.add_middleware(
        JWTAuthMiddleware,
        public_key=PUBLIC_KEY,
        exclude_paths=["/health", "/docs", "/openapi.json", "/redoc"],
        allowed_workspaces={"your-workspace-uuid"},
    )
    ```

    Users from other workspaces will receive a `403 Forbidden` response. See [Middleware — Restricting by Workspace](../sdk/middleware.md#restricting-by-workspace) for details.

## Step 3: First Protected Endpoint

Use `get_current_user` to access the authenticated user's JWT claims:

```python
from fastapi import Depends
from sentinel_auth.dependencies import get_current_user
from sentinel_auth.types import AuthenticatedUser

@app.get("/me")
async def whoami(user: AuthenticatedUser = Depends(get_current_user)):
    return {
        "user_id": str(user.user_id),
        "email": user.email,
        "name": user.name,
        "workspace_id": str(user.workspace_id),
        "workspace_role": user.workspace_role,
    }
```

The `AuthenticatedUser` dataclass gives you `user_id`, `email`, `name`, `workspace_id`, `workspace_slug`, `workspace_role`, and `groups`.

## Step 4: Workspace-Scoped Data

Use `get_workspace_id` to scope queries to the current workspace:

```python
from sentinel_auth.dependencies import get_workspace_id

@app.get("/notes")
async def list_notes(workspace_id: uuid.UUID = Depends(get_workspace_id)):
    return [n for n in all_notes if n.workspace_id == workspace_id]
```

This ensures users in workspace A never see notes from workspace B — even if they share the same database.

## Step 5: Enforce Workspace Roles

Use `require_role()` to restrict endpoints by workspace role level:

```python
from sentinel_auth.dependencies import require_role

@app.post("/notes", status_code=201)
async def create_note(
    body: CreateNoteRequest,
    user: AuthenticatedUser = Depends(require_role("editor")),
):
    # user is guaranteed to be at least an editor
    note = notes.create(
        title=body.title,
        content=body.content,
        workspace_id=user.workspace_id,
        owner_id=user.user_id,
    )
    return note
```

The role hierarchy is: `viewer < editor < admin < owner`. A user with `admin` role passes `require_role("editor")`.

## Step 6: Register Resources

When creating a resource that needs entity-level permissions, register it with the identity service:

```python
from sentinel_auth.permissions import PermissionClient

# Initialize in app lifespan
permissions = PermissionClient(
    base_url="http://localhost:9003",
    service_name="team-notes",
    service_key="your-service-key",
)

@app.post("/notes", status_code=201)
async def create_note(
    body: CreateNoteRequest,
    user: AuthenticatedUser = Depends(require_role("editor")),
):
    note = notes.create(...)

    # Register for ACL management
    await permissions.register_resource(
        resource_type="note",
        resource_id=note.id,
        workspace_id=user.workspace_id,
        owner_id=user.user_id,
        visibility="workspace",  # visible to all workspace members
    )
    return note
```

## Step 7: Entity-Level Permissions

Check if a user can view or edit a specific resource:

```python
@app.get("/notes/{note_id}")
async def get_note(
    note_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    token: str = Depends(get_token),
):
    note = notes.get(note_id)
    if not note:
        raise HTTPException(status_code=404)

    allowed = await permissions.can(
        token=token,
        resource_type="note",
        resource_id=note_id,
        action="view",
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="Access denied")

    return note
```

The permission system follows a 7-step resolution: owner check → visibility → direct user share → group share → workspace role → deny.

## Step 8: Share a Resource

Note owners can share with other users:

```python
@app.post("/notes/{note_id}/share")
async def share_note(
    note_id: uuid.UUID,
    body: ShareNoteRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    token: str = Depends(get_token),
):
    note = notes.get(note_id)
    if note.owner_id != user.user_id:
        raise HTTPException(status_code=403, detail="Only owner can share")

    # Forward to the identity service's permission share API
    await permissions._client.post(
        f"/permissions/{note_id}/share",
        json={
            "service_name": "team-notes",
            "resource_type": "note",
            "grantee_type": "user",
            "grantee_id": str(body.user_id),
            "permission": body.permission,  # "view" or "edit"
        },
        headers=permissions._headers(token),
    )
    return {"ok": True}
```

## Step 9: Custom RBAC Actions

Register service-specific actions on startup using `RoleClient`:

```python
from sentinel_auth.roles import RoleClient

roles = RoleClient(
    base_url="http://localhost:9003",
    service_name="team-notes",
    service_key="your-service-key",
)

# In your app lifespan
await roles.register_actions([
    {"action": "notes:export", "description": "Export notes as JSON"},
])
```

Then protect endpoints with `require_action()`:

```python
from sentinel_auth.dependencies import require_action

@app.get("/notes/export")
async def export_notes(
    user: AuthenticatedUser = Depends(require_action(roles, "notes:export")),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    workspace_notes = notes.list_by_workspace(workspace_id)
    return {"notes": workspace_notes}
```

An admin must create a role with the `notes:export` action and assign it to users through the admin panel before they can access this endpoint.

## Step 10: Build the Frontend

The frontend uses `@sentinel-auth/react` which handles the full OAuth + PKCE flow, token storage, automatic refresh, and authenticated API calls.

### Install dependencies

```bash
cd demo/frontend
npm install @sentinel-auth/js @sentinel-auth/react react-router-dom @tanstack/react-query
```

### Initialize the auth client

Create a shared `SentinelAuth` instance and an `apiFetch` wrapper that uses it for automatic Bearer token injection:

```typescript
// src/api/client.ts
import { SentinelAuth } from "@sentinel-auth/js";

const SENTINEL_URL =
  import.meta.env.VITE_SENTINEL_URL || "http://localhost:9003";

export const sentinelClient = new SentinelAuth({
  sentinelUrl: SENTINEL_URL,
});

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await sentinelClient.fetch(`/api${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...((options?.headers as Record<string, string>) ?? {}),
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}
```

`sentinelClient.fetch()` automatically attaches the Bearer token and retries once on 401 after refreshing.

### Wrap with SentinelAuthProvider

Pass the shared client into the React provider so all hooks can access it:

```tsx
// src/main.tsx
import { SentinelAuthProvider } from "@sentinel-auth/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { sentinelClient } from "./api/client";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <SentinelAuthProvider client={sentinelClient}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </SentinelAuthProvider>
  </StrictMode>,
);
```

### Use AuthGuard

Protect authenticated routes with `AuthGuard`. The `/auth/callback` route must stay **outside** the guard since the user isn't authenticated yet:

```tsx
// src/App.tsx
import { AuthGuard } from "@sentinel-auth/react";
import { Route, Routes } from "react-router-dom";
import { AuthCallback } from "./pages/AuthCallback";
import { Login } from "./pages/Login";
import { NoteList } from "./pages/NoteList";

export default function App() {
  return (
    <Routes>
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route
        path="*"
        element={
          <AuthGuard
            fallback={<Login />}
            loading={<div>Loading...</div>}
          >
            <Routes>
              <Route path="/" element={<NoteList />} />
            </Routes>
          </AuthGuard>
        }
      />
    </Routes>
  );
}
```

### Login page

Call `login("google")` to start the OAuth flow. PKCE challenge generation and the redirect to Sentinel are handled automatically:

```tsx
// src/pages/Login.tsx
import { useAuth } from "@sentinel-auth/react";

export function Login() {
  const { login } = useAuth();

  return (
    <button onClick={() => login("google")}>
      Sign in with Google
    </button>
  );
}
```

### OAuth callback

After the IdP redirects back, the callback page receives an authorization code. Use `getWorkspaces()` to fetch available workspaces, then `selectWorkspace()` to complete the token exchange:

```tsx
// src/pages/AuthCallback.tsx
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth, type WorkspaceOption } from "@sentinel-auth/react";

export function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { getWorkspaces, selectWorkspace } = useAuth();
  const code = searchParams.get("code");

  const [workspaces, setWorkspaces] = useState<WorkspaceOption[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!code) return;

    getWorkspaces(code).then(async (ws) => {
      if (ws.length === 1) {
        // Single workspace — auto-select
        await selectWorkspace(code, ws[0].id);
        navigate("/", { replace: true });
        return;
      }
      // Multiple workspaces — show picker
      setWorkspaces(ws);
      setLoading(false);
    });
  }, [code]);

  async function handleSelect(workspaceId: string) {
    if (!code) return;
    await selectWorkspace(code, workspaceId);
    navigate("/", { replace: true });
  }

  if (loading) return <div>Signing you in...</div>;

  return (
    <div>
      <h2>Select Workspace</h2>
      {workspaces.map((ws) => (
        <button key={ws.id} onClick={() => handleSelect(ws.id)}>
          {ws.name} ({ws.role})
        </button>
      ))}
    </div>
  );
}
```

The flow is: `login()` → IdP redirect → `getWorkspaces(code)` → `selectWorkspace(code, wsId)` → JWT tokens stored automatically.

### Access user context

Use `useUser()` in any component inside `AuthGuard` to access the authenticated user:

```tsx
import { useUser, useAuth } from "@sentinel-auth/react";

function Layout({ children }) {
  const user = useUser();
  const { logout } = useAuth();

  return (
    <div>
      <nav>
        <span>{user.name} — {user.workspaceSlug} ({user.workspaceRole})</span>
        <button onClick={logout}>Logout</button>
      </nav>
      {children}
    </div>
  );
}
```

### Check roles

Use `useHasRole()` for conditional UI based on workspace roles:

```tsx
import { useHasRole } from "@sentinel-auth/react";

function NoteList() {
  const canCreate = useHasRole("editor");

  return (
    <div>
      {canCreate && <button>New Note</button>}
      {/* ... */}
    </div>
  );
}
```

The role hierarchy is `viewer < editor < admin < owner` — a user with `admin` role passes `useHasRole("editor")`.

### Authenticated API calls

Use the `apiFetch` wrapper (or `useAuthFetch()`) with React Query for data fetching:

```tsx
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../api/client";

function NoteList() {
  const { data: notes } = useQuery({
    queryKey: ["notes"],
    queryFn: () => apiFetch<Note[]>("/notes"),
  });

  return (
    <ul>
      {notes?.map((note) => (
        <li key={note.id}>{note.title}</li>
      ))}
    </ul>
  );
}
```

## Step 11: Configure and Run

### Register the client app

Before the frontend can authenticate, register it as a client app in Sentinel with its callback URL.

In the admin panel, go to **Client Apps** → **Add Client App** and add:

- **Name**: `team-notes-frontend`
- **Redirect URIs**: `http://localhost:9101/auth/callback`

### Register the service app

The demo backend needs a service key to call Sentinel's permission and role APIs.

In the admin panel, go to **Service Apps** → **Add Service App**:

- **Name**: `team-notes-backend`
- Toggle **Dev Mode** on

Copy the generated `sk_...` key and add it to the backend's `.env`:

```dotenv
SENTINEL_SERVICE_KEY=sk_...
```

### Start the services

=== "Docker (Sentinel)"

    ```bash
    # Sentinel is already running via Docker
    # Demo backend
    cd demo/backend && uv sync && uv run python -m src.main

    # Demo frontend (in another terminal)
    cd demo/frontend && npm install && npm run dev
    ```

=== "From Source"

    ```bash
    # Terminal 1: Sentinel
    make infra && make start

    # Terminal 2: Demo backend
    cd demo/backend && uv sync && uv run python -m src.main

    # Terminal 3: Demo frontend
    cd demo/frontend && npm install && npm run dev
    ```

Open [http://localhost:9101](http://localhost:9101) and sign in with Google.

## Summary

| What | How | SDK API |
|------|-----|---------|
| Authenticate users | JWT middleware on every request | `JWTAuthMiddleware` |
| Get user context | FastAPI dependency | `get_current_user` |
| Isolate workspaces | Filter data by workspace_id | `get_workspace_id` |
| Enforce roles | Minimum role check | `require_role("editor")` |
| Register resources | On creation, register for ACLs | `permissions.register_resource()` |
| Check entity access | Per-resource permission check | `permissions.can()` |
| Share resources | Grant access to other users | Permission share API |
| Custom RBAC | Register actions, check at runtime | `require_action(client, "action")` |
| Frontend auth | React provider + PKCE | `SentinelAuthProvider`, `useAuth()` |
| OAuth callback | Workspace selection flow | `getWorkspaces()`, `selectWorkspace()` |
| Authenticated fetch | Auto Bearer token + refresh | `sentinelClient.fetch()`, `useAuthFetch()` |

## Next Steps

- [Python SDK Reference](../sdk/index.md) — full API documentation for all SDK modules
- [JS SDK Reference](../js-sdk/index.md) — `@sentinel-auth/js` and `@sentinel-auth/react` API docs
- [Integration Guide](../sdk/integration.md) — detailed 9-step integration reference
- [Examples](../sdk/examples.md) — common patterns and recipes
