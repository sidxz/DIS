import uuid
from datetime import UTC, datetime, timedelta

import jwt

from src.config import settings

_private_key: str | None = None
_public_key: str | None = None


def _get_private_key() -> str:
    global _private_key
    if _private_key is None:
        _private_key = settings.jwt_private_key_path.read_text()
    return _private_key


def _get_public_key() -> str:
    global _public_key
    if _public_key is None:
        _public_key = settings.jwt_public_key_path.read_text()
    return _public_key


def get_public_key() -> str:
    return _get_public_key()


_AUD_ACCESS = "sentinel:access"
_AUD_ADMIN = "sentinel:admin"
_AUD_REFRESH = "sentinel:refresh"
_AUD_AUTHZ = "sentinel:authz"
_ISSUER = settings.base_url


def create_access_token(
    user_id: uuid.UUID,
    email: str,
    name: str,
    workspace_id: uuid.UUID,
    workspace_slug: str,
    workspace_role: str,
    groups: list[uuid.UUID],
) -> str:
    now = datetime.now(UTC)
    payload = {
        "iss": _ISSUER,
        "sub": str(user_id),
        "jti": str(uuid.uuid4()),
        "aud": _AUD_ACCESS,
        "email": email,
        "name": name,
        "wid": str(workspace_id),
        "wslug": workspace_slug,
        "wrole": workspace_role,
        "groups": [str(g) for g in groups],
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "type": "access",
    }
    return jwt.encode(payload, _get_private_key(), algorithm=settings.jwt_algorithm)


def create_admin_token(user_id: uuid.UUID, email: str, name: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "iss": _ISSUER,
        "sub": str(user_id),
        "jti": str(uuid.uuid4()),
        "aud": _AUD_ADMIN,
        "email": email,
        "name": name,
        "admin": True,
        "iat": now,
        "exp": now + timedelta(minutes=settings.admin_token_expire_minutes),
        "type": "admin_access",
    }
    return jwt.encode(payload, _get_private_key(), algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: uuid.UUID, family_id: str | None = None) -> str:
    now = datetime.now(UTC)
    payload = {
        "iss": _ISSUER,
        "sub": str(user_id),
        "jti": str(uuid.uuid4()),
        "fid": family_id or str(uuid.uuid4()),
        "aud": _AUD_REFRESH,
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
        "type": "refresh",
    }
    return jwt.encode(payload, _get_private_key(), algorithm=settings.jwt_algorithm)


def create_authz_token(
    user_id: uuid.UUID,
    idp_sub: str,
    workspace_id: uuid.UUID,
    workspace_slug: str,
    workspace_role: str,
    actions: list[str],
    service_name: str,
) -> str:
    """Create a short-lived authorization-only JWT.

    This token carries workspace role and RBAC actions but NOT identity.
    Identity is proven by the IdP token (validated separately).
    The idp_sub claim binds this token to a specific IdP identity.
    The svc claim binds the token to a specific service (prevents cross-service replay).
    """
    now = datetime.now(UTC)
    payload = {
        "iss": _ISSUER,
        "sub": str(user_id),
        "jti": str(uuid.uuid4()),  # Security: jti enables revocation via denylist
        "idp_sub": idp_sub,
        "svc": service_name,
        "wid": str(workspace_id),
        "wslug": workspace_slug,
        "wrole": workspace_role,
        "actions": actions,
        "aud": _AUD_AUTHZ,
        "iat": now,
        "exp": now + timedelta(minutes=settings.authz_token_expire_minutes),
        "type": "authz",
    }
    return jwt.encode(payload, _get_private_key(), algorithm=settings.jwt_algorithm)


def decode_token(token: str, audience: str | list[str]) -> dict:
    """Decode and validate a JWT.

    Audience is required — callers must explicitly declare expected audience.
    Decode algorithm is hardcoded to RS256 to prevent algorithm confusion attacks.
    """
    return jwt.decode(
        token,
        _get_public_key(),
        algorithms=["RS256"],  # Security: hardcode to prevent algorithm substitution
        audience=audience,
        issuer=_ISSUER,
    )


def _assert_algorithm() -> None:
    """Startup assertion: encoding algorithm must be RS256."""
    if settings.jwt_algorithm != "RS256":
        raise RuntimeError(
            f"jwt_algorithm must be RS256, got {settings.jwt_algorithm!r}"
        )


_assert_algorithm()
