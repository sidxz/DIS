"""Dual-token middleware for AuthZ mode.

Validates both an IdP token (identity) and a Sentinel authz token
(authorization), checking that the idp_sub claims match.
"""

import uuid

import jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from sentinel_auth.types import AuthenticatedUser


class AuthzMiddleware(BaseHTTPMiddleware):
    """Validates IdP token + Sentinel authz token on each request.

    IdP token: ``Authorization: Bearer <idp_token>``
    Authz token: ``X-Authz-Token: <authz_token>``

    Both must be valid and their ``sub``/``idp_sub`` claims must match.
    """

    def __init__(
        self,
        app: ASGIApp,
        idp_public_key: str,
        sentinel_public_key: str,
        idp_algorithm: str = "RS256",
        sentinel_algorithm: str = "RS256",
        sentinel_audience: str = "sentinel:authz",
        exclude_paths: list[str] | None = None,
    ):
        super().__init__(app)
        self.idp_public_key = idp_public_key
        self.sentinel_public_key = sentinel_public_key
        self.idp_algorithm = idp_algorithm
        self.sentinel_algorithm = sentinel_algorithm
        self.sentinel_audience = sentinel_audience
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json"]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        # 1. Extract IdP token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing IdP token"})
        idp_token = auth_header.removeprefix("Bearer ")

        # 2. Extract authz token from X-Authz-Token header
        authz_token = request.headers.get("X-Authz-Token")
        if not authz_token:
            return JSONResponse(status_code=401, content={"detail": "Missing authz token"})

        # 3. Validate IdP token
        try:
            idp_payload = jwt.decode(
                idp_token,
                self.idp_public_key,
                algorithms=[self.idp_algorithm],
                options={"verify_aud": False},
            )
        except jwt.ExpiredSignatureError:
            return JSONResponse(status_code=401, content={"detail": "IdP token expired"})
        except jwt.InvalidTokenError:
            return JSONResponse(status_code=401, content={"detail": "Invalid IdP token"})

        # 4. Validate authz token
        try:
            authz_payload = jwt.decode(
                authz_token,
                self.sentinel_public_key,
                algorithms=[self.sentinel_algorithm],
                audience=self.sentinel_audience,
            )
        except jwt.ExpiredSignatureError:
            return JSONResponse(status_code=401, content={"detail": "Authz token expired"})
        except jwt.InvalidTokenError:
            return JSONResponse(status_code=401, content={"detail": "Invalid authz token"})

        # 5. Verify binding: IdP sub must match authz idp_sub
        idp_sub = idp_payload.get("sub", "")
        authz_idp_sub = authz_payload.get("idp_sub", "")
        if idp_sub != authz_idp_sub:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token binding mismatch: idp_sub does not match"},
            )

        # 6. Set user on request state
        try:
            request.state.user = AuthenticatedUser(
                user_id=uuid.UUID(authz_payload["sub"]),
                email=idp_payload.get("email", ""),
                name=idp_payload.get("name", ""),
                workspace_id=uuid.UUID(authz_payload["wid"]),
                workspace_slug=authz_payload.get("wslug", ""),
                workspace_role=authz_payload["wrole"],
                groups=[],
            )
            request.state.token = authz_token
            request.state.idp_token = idp_token
        except (KeyError, ValueError):
            return JSONResponse(status_code=401, content={"detail": "Invalid token claims"})

        return await call_next(request)
