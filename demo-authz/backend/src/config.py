import httpx
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from jwt.algorithms import RSAAlgorithm
from pydantic_settings import BaseSettings, SettingsConfigDict

from sentinel_auth import Sentinel


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    sentinel_url: str = "http://localhost:9003"
    service_name: str = "team-notes"
    service_api_key: str = ""
    idp_public_key: str = ""
    idp_jwks_url: str = "https://www.googleapis.com/oauth2/v3/certs"
    host: str = "0.0.0.0"
    port: int = 9200
    frontend_url: str = "http://localhost:9201"


settings = Settings()


def _resolve_idp_public_key() -> str:
    """Get IdP public key from config or fetch from JWKS URL."""
    if settings.idp_public_key:
        return settings.idp_public_key

    # Fetch first key from IdP's JWKS endpoint
    resp = httpx.get(settings.idp_jwks_url, timeout=10.0)
    resp.raise_for_status()
    jwks = resp.json()
    key_data = jwks["keys"][0]
    pub_key = RSAAlgorithm.from_jwk(key_data)
    return pub_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()


sentinel = Sentinel(
    base_url=settings.sentinel_url,
    service_name=settings.service_name,
    service_key=settings.service_api_key,
    mode="authz",
    idp_public_key=_resolve_idp_public_key(),
    actions=[
        {"action": "notes:export", "description": "Export notes as JSON"},
        {"action": "notes:bulk-delete", "description": "Bulk delete notes"},
    ],
)
