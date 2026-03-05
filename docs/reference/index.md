# SDK Reference

This section contains API reference documentation for the `daikon-identity-sdk` Python package, auto-generated from source code docstrings using [mkdocstrings](https://mkdocstrings.github.io/).

Each page corresponds to a module in the `identity_sdk` package:

| Module | Description |
|--------|-------------|
| [Types](types.md) | Data classes (`AuthenticatedUser`, `WorkspaceContext`) used throughout the SDK |
| [Middleware](middleware.md) | `JWTAuthMiddleware` for validating tokens on incoming requests |
| [Dependencies](dependencies.md) | FastAPI dependency functions for injecting user/workspace context |
| [Permissions](permissions.md) | `PermissionClient` for interacting with the permissions API |

## Usage

Install the SDK in your service:

```bash
uv add daikon-identity-sdk
```

Then import what you need:

```python
from identity_sdk.types import AuthenticatedUser
from identity_sdk.middleware import JWTAuthMiddleware
from identity_sdk.dependencies import get_current_user, get_workspace
from identity_sdk.permissions import PermissionClient
```

!!! note "Docstring format"
    All docstrings follow Google style. Parameters, return types, and raised exceptions are documented inline in the source and rendered here automatically.
