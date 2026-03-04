import uuid

import jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from identity_sdk.types import AuthenticatedUser


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Validates JWT access tokens and sets request.state.user."""

    def __init__(
        self,
        app,
        public_key: str,
        algorithm: str = "RS256",
        exclude_paths: list[str] | None = None,
    ):
        super().__init__(app)
        self.public_key = public_key
        self.algorithm = algorithm
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json"]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip auth for excluded paths
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing or invalid Authorization header"})

        token = auth_header.removeprefix("Bearer ")
        try:
            payload = jwt.decode(token, self.public_key, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            return JSONResponse(status_code=401, content={"detail": "Token has expired"})
        except jwt.InvalidTokenError as e:
            return JSONResponse(status_code=401, content={"detail": f"Invalid token: {e}"})

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
