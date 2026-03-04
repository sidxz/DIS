"""
Demo app that simulates how a consuming application (like docu-store) would
integrate with the Daikon Identity Service via the SDK.

This demo:
1. Generates test JWT keys and tokens (no real OAuth needed)
2. Starts a sample FastAPI app protected by the SDK middleware
3. Demonstrates workspace-scoped routes with role enforcement
4. Shows permission client usage for entity-level checks

Usage:
    cd identity-service
    uv run python demo/demo_app.py

Then visit http://localhost:9000/docs to try the endpoints.
A test JWT is printed to stdout — use it in the Authorization header.
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt as pyjwt
import uvicorn
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI

from identity_sdk.dependencies import get_current_user, get_workspace_id, require_role
from identity_sdk.middleware import JWTAuthMiddleware
from identity_sdk.types import AuthenticatedUser

# ---------------------------------------------------------------------------
# 1. Generate ephemeral RSA keys (no files needed)
# ---------------------------------------------------------------------------
_private_key_obj = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PRIVATE_KEY = _private_key_obj.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode()
PUBLIC_KEY = (
    _private_key_obj.public_key()
    .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    .decode()
)

# ---------------------------------------------------------------------------
# 2. Create test data
# ---------------------------------------------------------------------------
TEST_USER_ID = uuid.uuid4()
TEST_WORKSPACE_ID = uuid.uuid4()
TEST_GROUP_ID = uuid.uuid4()

DEMO_USERS = {
    "owner": {
        "sub": str(TEST_USER_ID),
        "email": "alice@example.com",
        "name": "Alice (Owner)",
        "wid": str(TEST_WORKSPACE_ID),
        "wslug": "acme-corp",
        "wrole": "owner",
        "groups": [str(TEST_GROUP_ID)],
    },
    "editor": {
        "sub": str(uuid.uuid4()),
        "email": "bob@example.com",
        "name": "Bob (Editor)",
        "wid": str(TEST_WORKSPACE_ID),
        "wslug": "acme-corp",
        "wrole": "editor",
        "groups": [],
    },
    "viewer": {
        "sub": str(uuid.uuid4()),
        "email": "carol@example.com",
        "name": "Carol (Viewer)",
        "wid": str(TEST_WORKSPACE_ID),
        "wslug": "acme-corp",
        "wrole": "viewer",
        "groups": [],
    },
}


def _make_token(user_data: dict, expire_hours: int = 24) -> str:
    payload = {
        **user_data,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(hours=expire_hours),
        "type": "access",
    }
    return pyjwt.encode(payload, PRIVATE_KEY, algorithm="RS256")


# ---------------------------------------------------------------------------
# 3. Build the demo FastAPI app (simulates docu-store or any consuming app)
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Demo App (SDK Consumer)",
    description="Demonstrates how an app uses the Daikon Identity SDK",
    version="0.1.0",
)

app.add_middleware(
    JWTAuthMiddleware,
    public_key=PUBLIC_KEY,
    exclude_paths=["/health", "/docs", "/openapi.json", "/redoc", "/tokens"],
)

# In-memory "database" for the demo
ITEMS: dict[str, dict] = {}


# --- Public route: get test tokens ---
@app.get("/tokens", tags=["demo"])
async def get_test_tokens():
    """Returns pre-built JWTs for testing. Copy one and use as Bearer token."""
    return {
        role: {
            "token": _make_token(data),
            "user": data["name"],
            "role": data["wrole"],
            "usage": f'curl -H "Authorization: Bearer {_make_token(data)}" http://localhost:9000/me',
        }
        for role, data in DEMO_USERS.items()
    }


# --- Protected routes ---
@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}


@app.get("/me", tags=["user"])
async def whoami(user: AuthenticatedUser = Depends(get_current_user)):
    """Shows the authenticated user's context extracted from the JWT."""
    return {
        "user_id": str(user.user_id),
        "email": user.email,
        "name": user.name,
        "workspace_id": str(user.workspace_id),
        "workspace_slug": user.workspace_slug,
        "workspace_role": user.workspace_role,
        "groups": [str(g) for g in user.groups],
        "is_admin": user.is_admin,
        "is_editor": user.is_editor,
    }


@app.get("/items", tags=["items"])
async def list_items(
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    """List items scoped to the current workspace."""
    return [
        item for item in ITEMS.values() if item["workspace_id"] == str(workspace_id)
    ]


@app.post("/items", tags=["items"])
async def create_item(
    name: str,
    user: AuthenticatedUser = Depends(require_role("editor")),
):
    """Create an item. Requires at least 'editor' role."""
    item_id = str(uuid.uuid4())
    item = {
        "id": item_id,
        "name": name,
        "workspace_id": str(user.workspace_id),
        "owner_id": str(user.user_id),
        "created_by": user.name,
    }
    ITEMS[item_id] = item
    return item


@app.delete("/items/{item_id}", tags=["items"])
async def delete_item(
    item_id: str,
    user: AuthenticatedUser = Depends(require_role("admin")),
):
    """Delete an item. Requires at least 'admin' role."""
    if item_id not in ITEMS:
        return {"error": "not found"}
    del ITEMS[item_id]
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# 4. Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("DAIKON IDENTITY SDK — DEMO APP")
    print("=" * 70)
    print(f"\nWorkspace: acme-corp ({TEST_WORKSPACE_ID})")
    print(f"Group:     {TEST_GROUP_ID}")
    print("\nTest tokens (valid for 24h):")
    print("-" * 70)
    for role, data in DEMO_USERS.items():
        token = _make_token(data)
        print(f"\n  [{role.upper()}] {data['name']}")
        print(f"  Token: {token[:50]}...")
    print("\n" + "-" * 70)
    print("\nEndpoints:")
    print("  GET  /tokens  — Get full test tokens (no auth needed)")
    print("  GET  /me      — Show current user context")
    print("  GET  /items   — List items (any authenticated user)")
    print("  POST /items   — Create item (editor+ only)")
    print("  DELETE /items/{id} — Delete item (admin+ only)")
    print(f"\nVisit: http://localhost:9000/docs")
    print("=" * 70 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=9000)
