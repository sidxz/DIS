"""Starlette/FastAPI middleware for JWT access token validation.

Add this middleware to your FastAPI app to automatically validate
JWT tokens on incoming requests and populate ``request.state.user``
with an ``AuthenticatedUser`` instance.
"""

import uuid

import jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from sentinel_auth.types import AuthenticatedUser


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Validates JWT access tokens and sets ``request.state.user``.

    For each incoming request (except excluded paths), this middleware:

    1. Extracts the ``Authorization: Bearer <token>`` header
    2. Decodes and validates the JWT using the provided public key
    3. Sets ``request.state.user`` to an ``AuthenticatedUser`` instance
    4. Returns 401 if the token is missing, expired, or invalid

    Args:
        app: The ASGI application to wrap.
        public_key: RSA public key (PEM format) used to verify JWT signatures.
            Obtain this from the identity service's ``keys/public.pem``.
        algorithm: JWT signing algorithm. Defaults to ``"RS256"``.
        exclude_paths: List of path prefixes to skip authentication for.
            Defaults to ``["/health", "/docs", "/openapi.json"]``.
        allowed_workspaces: Optional set of workspace IDs (as strings) that
            are permitted to access this service. ``None`` (default) allows
            all workspaces. Returns 403 if the JWT's workspace is not in the set.

    Example:
        ```python
        from pathlib import Path
        from sentinel_auth.middleware import JWTAuthMiddleware

        public_key = Path("keys/public.pem").read_text()

        app.add_middleware(
            JWTAuthMiddleware,
            public_key=public_key,
            exclude_paths=["/health", "/docs", "/openapi.json"],
        )
        ```
    """

    def __init__(
        self,
        app: ASGIApp,
        public_key: str,
        algorithm: str = "RS256",
        exclude_paths: list[str] | None = None,
        allowed_workspaces: set[str] | None = None,
    ):
        super().__init__(app)
        self.public_key = public_key
        self.algorithm = algorithm
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json"]
        self.allowed_workspaces = allowed_workspaces

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip auth for excluded paths
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        token = auth_header.removeprefix("Bearer ")
        try:
            payload = jwt.decode(token, self.public_key, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            return JSONResponse(status_code=401, content={"detail": "Token has expired"})
        except jwt.InvalidTokenError as e:
            return JSONResponse(status_code=401, content={"detail": f"Invalid token: {e}"})

        if self.allowed_workspaces is not None and payload["wid"] not in self.allowed_workspaces:
            return JSONResponse(
                status_code=403,
                content={"detail": "Workspace not permitted for this service"},
            )

        request.state.user = AuthenticatedUser(
            user_id=uuid.UUID(payload["sub"]),
            email=payload["email"],
            name=payload["name"],
            workspace_id=uuid.UUID(payload["wid"]),
            workspace_slug=payload["wslug"],
            workspace_role=payload["wrole"],
            groups=[uuid.UUID(g) for g in payload.get("groups", [])],
        )

        return await call_next(request)
