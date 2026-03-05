# Integration Guide

This guide walks through adding authentication and authorization to an existing FastAPI service using the Daikon Identity SDK. By the end, your service will validate JWTs, enforce workspace isolation, and check entity-level permissions.

## Prerequisites

- A running Daikon Identity Service instance
- The identity service's RS256 public key (`keys/public.pem`)
- A service API key registered with the identity service
- An existing FastAPI application to integrate with

## Step 1: Install the SDK

Add the SDK to your project:

```bash
uv add daikon-identity-sdk
```

Or for local development against the monorepo:

```toml
# pyproject.toml
[project]
dependencies = [
    "daikon-identity-sdk",
]

[tool.uv.sources]
daikon-identity-sdk = { path = "../identity-service/sdk", editable = true }
```

Then sync:

```bash
uv sync
```

## Step 2: Add JWT Middleware

Add the `JWTAuthMiddleware` to your FastAPI application. This validates Bearer tokens on every request and populates `request.state.user`.

**Before:**

```python
from fastapi import FastAPI

app = FastAPI(title="My Service")
```

**After:**

```python
from pathlib import Path

from fastapi import FastAPI
from identity_sdk.middleware import JWTAuthMiddleware

app = FastAPI(title="My Service")

PUBLIC_KEY = Path("keys/public.pem").read_text()

app.add_middleware(
    JWTAuthMiddleware,
    public_key=PUBLIC_KEY,
    exclude_paths=["/health", "/docs", "/openapi.json", "/redoc"],
)
```

Every authenticated request now has an `AuthenticatedUser` on `request.state.user`.

## Step 3: Create Auth Dependencies

Set up reusable dependencies for your routes. Create an `auth.py` module (or add to an existing dependencies module):

```python
# src/dependencies/auth.py
from identity_sdk.dependencies import (
    get_current_user,
    get_workspace_id,
    get_workspace_context,
    require_role,
)
from identity_sdk.types import AuthenticatedUser, WorkspaceContext

# Re-export for convenience -- routes import from here
__all__ = [
    "get_current_user",
    "get_workspace_id",
    "get_workspace_context",
    "require_role",
    "AuthenticatedUser",
    "WorkspaceContext",
]
```

You can also add application-specific dependencies that build on the SDK:

```python
# src/dependencies/auth.py (continued)
from fastapi import Depends, Request
from identity_sdk.permissions import PermissionClient


def get_permissions(request: Request) -> PermissionClient:
    """Retrieve the PermissionClient from app state."""
    return request.app.state.permissions


def get_token(request: Request) -> str:
    """Extract the raw JWT token from the Authorization header."""
    return request.headers["Authorization"].removeprefix("Bearer ")
```

## Step 4: Update API Routes

Inject authentication context into your route handlers.

**Before** (no auth):

```python
@router.get("/documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    stmt = select(Document)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/documents")
async def create_document(
    body: CreateDocumentRequest,
    db: AsyncSession = Depends(get_db),
):
    document = Document(title=body.title, content=body.content)
    db.add(document)
    await db.commit()
    return document


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    await db.execute(delete(Document).where(Document.id == doc_id))
    await db.commit()
```

**After** (with auth):

```python
from identity_sdk.dependencies import get_current_user, get_workspace_id, require_role
from identity_sdk.types import AuthenticatedUser


@router.get("/documents")
async def list_documents(
    workspace_id: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
):
    # Scoped to workspace
    stmt = select(Document).where(Document.workspace_id == workspace_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/documents")
async def create_document(
    body: CreateDocumentRequest,
    user: AuthenticatedUser = Depends(require_role("editor")),
    db: AsyncSession = Depends(get_db),
):
    document = Document(
        title=body.title,
        content=body.content,
        workspace_id=user.workspace_id,
        owner_id=user.user_id,
    )
    db.add(document)
    await db.commit()
    return document


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: UUID,
    user: AuthenticatedUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        delete(Document).where(
            Document.id == doc_id,
            Document.workspace_id == user.workspace_id,
        )
    )
    await db.commit()
```

## Step 5: Add Workspace and Owner Fields to Domain Entities

Update your SQLAlchemy models to include `workspace_id` and `owner_id` columns:

**Before:**

```python
from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

class Document(Base):
    __tablename__ = "documents"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
```

**After:**

```python
from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

class Document(Base):
    __tablename__ = "documents"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    workspace_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    owner_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
```

Create an Alembic migration for the schema change:

```bash
alembic revision --autogenerate -m "add workspace_id and owner_id to documents"
alembic upgrade head
```

## Step 6: Filter All Queries by Workspace

Every database query that returns user-visible data must be scoped to the current workspace. This prevents data leakage between workspaces.

```python
# Always include workspace_id in WHERE clauses
stmt = select(Document).where(
    Document.workspace_id == workspace_id,
)

# Also scope updates and deletes
stmt = (
    update(Document)
    .where(
        Document.id == doc_id,
        Document.workspace_id == workspace_id,
    )
    .values(title=new_title)
)
```

Consider creating a base query helper:

```python
def workspace_query(model, workspace_id: UUID):
    """Base query scoped to a workspace."""
    return select(model).where(model.workspace_id == workspace_id)
```

## Step 7: Add Workspace Context to Vector Stores

If your service uses vector databases (e.g., for semantic search), include `workspace_id` in the metadata so you can filter at query time:

```python
# When indexing
await vector_store.add(
    documents=[chunk.text for chunk in chunks],
    metadatas=[
        {
            "document_id": str(document.id),
            "workspace_id": str(document.workspace_id),
            "owner_id": str(document.owner_id),
        }
        for chunk in chunks
    ],
    ids=[str(chunk.id) for chunk in chunks],
)

# When querying -- always filter by workspace
results = await vector_store.query(
    query_text=query,
    where={"workspace_id": str(workspace_id)},
    n_results=10,
)
```

## Step 8: Register Resources with the Identity Service

When creating resources that need entity-level access control, register them with the identity service's permission system.

Set up the `PermissionClient` in your application lifespan:

```python
from contextlib import asynccontextmanager

from identity_sdk.permissions import PermissionClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.permissions = PermissionClient(
        base_url="http://identity-service:8000",
        service_name="my-service",
        service_key="sk_my_service_key",
    )
    yield
    await app.state.permissions.close()

app = FastAPI(title="My Service", lifespan=lifespan)
```

Then register resources on creation:

```python
@router.post("/documents")
async def create_document(
    body: CreateDocumentRequest,
    request: Request,
    user: AuthenticatedUser = Depends(require_role("editor")),
    db: AsyncSession = Depends(get_db),
):
    document = Document(
        title=body.title,
        content=body.content,
        workspace_id=user.workspace_id,
        owner_id=user.user_id,
    )
    db.add(document)
    await db.commit()

    # Register with identity service for ACL management
    await request.app.state.permissions.register_resource(
        resource_type="document",
        resource_id=document.id,
        workspace_id=user.workspace_id,
        owner_id=user.user_id,
        visibility="workspace",
    )

    return document
```

## Step 9: Network Configuration

In a Docker Compose environment, your service and the identity service must be on the same network:

```yaml
# docker-compose.yml
services:
  identity-service:
    build: ./identity-service/service
    networks:
      - backend
    ports:
      - "8100:8000"
    volumes:
      - identity-keys:/app/keys

  my-service:
    build: ./my-service
    networks:
      - backend
    ports:
      - "8200:8000"
    environment:
      IDENTITY_SERVICE_URL: "http://identity-service:8000"
      IDENTITY_SERVICE_KEY: "sk_my_service_key"
    volumes:
      - identity-keys:/app/keys:ro
    depends_on:
      - identity-service

networks:
  backend:
    driver: bridge

volumes:
  identity-keys:
```

Key points:

- Both services are on the `backend` network so they can reach each other by service name
- The identity service's key directory is shared as a read-only volume
- The service URL uses the Docker service name (`identity-service`), not `localhost`

## Complete Example: Fully Integrated Application

Here is a minimal but complete FastAPI application with all integration steps applied:

```python
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from identity_sdk.dependencies import get_current_user, get_workspace_id, require_role
from identity_sdk.middleware import JWTAuthMiddleware
from identity_sdk.permissions import PermissionClient
from identity_sdk.types import AuthenticatedUser


# --- Lifespan ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.permissions = PermissionClient(
        base_url=os.environ["IDENTITY_SERVICE_URL"],
        service_name="my-service",
        service_key=os.environ["IDENTITY_SERVICE_KEY"],
    )
    yield
    await app.state.permissions.close()


# --- App ---

app = FastAPI(title="My Service", lifespan=lifespan)

PUBLIC_KEY = Path("keys/public.pem").read_text()
app.add_middleware(
    JWTAuthMiddleware,
    public_key=PUBLIC_KEY,
    exclude_paths=["/health", "/docs", "/openapi.json"],
)


# --- Routes ---

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/documents")
async def list_documents(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    token = request.headers["Authorization"].removeprefix("Bearer ")
    resource_ids, has_full_access = await request.app.state.permissions.accessible(
        token=token,
        resource_type="document",
        action="view",
        workspace_id=workspace_id,
    )
    # Use resource_ids to filter your database query
    # If has_full_access is True, skip filtering
    ...


@app.post("/documents")
async def create_document(
    request: Request,
    user: AuthenticatedUser = Depends(require_role("editor")),
):
    doc_id = uuid.uuid4()
    # ... create document in database ...

    await request.app.state.permissions.register_resource(
        resource_type="document",
        resource_id=doc_id,
        workspace_id=user.workspace_id,
        owner_id=user.user_id,
        visibility="workspace",
    )
    return {"id": str(doc_id)}


@app.get("/documents/{doc_id}")
async def get_document(
    doc_id: uuid.UUID,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    token = request.headers["Authorization"].removeprefix("Bearer ")
    allowed = await request.app.state.permissions.can(
        token=token,
        resource_type="document",
        resource_id=doc_id,
        action="view",
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="Access denied")
    # ... fetch and return document ...
```

## Next Steps

- [Permission Client](permission-client.md) -- detailed API reference for all permission methods
- [Examples](examples.md) -- common patterns and recipes
