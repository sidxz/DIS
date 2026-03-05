# Installation

## Install from PyPI

Using [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv add sentinel-auth-sdk
```

Using pip:

```bash
pip install sentinel-auth-sdk
```

This installs the SDK and all its dependencies (`pyjwt[crypto]`, `httpx`, `cryptography`, `pydantic`, `starlette`, `fastapi`).

## Editable Install for Local Development

If you are developing against a local checkout of the identity service monorepo, you can install the SDK in editable mode so changes to the SDK source are reflected immediately.

Add the SDK as a dependency in your service's `pyproject.toml`:

```toml
[project]
dependencies = [
    "sentinel-auth-sdk",
]
```

Then configure uv to resolve it from the local path by adding a `[tool.uv.sources]` entry:

```toml
[tool.uv.sources]
sentinel-auth-sdk = { path = "../identity-service/sdk", editable = true }
```

Run `uv sync` to install:

```bash
uv sync
```

The SDK will be installed as an editable link. Any changes you make to the SDK code under `identity-service/sdk/src/sentinel_auth/` will be picked up without reinstalling.

## Verify Installation

Confirm the SDK is installed and importable:

```python
>>> from sentinel_auth.types import AuthenticatedUser, WorkspaceContext
>>> from sentinel_auth.middleware import JWTAuthMiddleware
>>> from sentinel_auth.dependencies import get_current_user
>>> from sentinel_auth.permissions import PermissionClient
```

## Public Key Setup

The SDK's JWT middleware validates tokens using the identity service's RS256 public key. You need a copy of this key available to your service at runtime.

### Option 1: File on Disk

Copy the public key from the identity service:

```bash
cp /path/to/identity-service/keys/public.pem ./keys/public.pem
```

Load it in your application:

```python
from pathlib import Path

PUBLIC_KEY = Path("keys/public.pem").read_text()
```

### Option 2: Environment Variable

Set the public key as an environment variable (useful for containerized deployments):

```bash
export IDENTITY_PUBLIC_KEY="$(cat keys/public.pem)"
```

Load it in your application:

```python
import os

PUBLIC_KEY = os.environ["IDENTITY_PUBLIC_KEY"]
```

### Option 3: Shared Volume (Docker)

In a Docker Compose setup, mount the identity service's key directory as a read-only volume:

```yaml
services:
  my-service:
    volumes:
      - identity-keys:/app/keys:ro

  identity-service:
    volumes:
      - identity-keys:/app/keys

volumes:
  identity-keys:
```

## Requirements

- **Python** >= 3.12
- **Identity Service** running and accessible over the network (for permission client calls)
- **Public key** from the identity service (for JWT validation)

## Next Steps

- [Middleware](middleware.md) -- configure the JWT validation middleware
- [Integration Guide](integration.md) -- full walkthrough of adding auth to your service
