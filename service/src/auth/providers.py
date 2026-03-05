from authlib.integrations.starlette_client import OAuth

from src.config import settings

oauth = OAuth()

# Google (OAuth2 + OpenID Connect)
if settings.google_client_id:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
        code_challenge_method="S256",
    )

# GitHub (OAuth2 — not full OIDC, uses userinfo endpoint)
# Note: GitHub does not support PKCE as of 2025
if settings.github_client_id:
    oauth.register(
        name="github",
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "user:email"},
    )

# Microsoft EntraID (OAuth2 + OIDC)
if settings.entra_client_id and settings.entra_tenant_id:
    oauth.register(
        name="entra_id",
        client_id=settings.entra_client_id,
        client_secret=settings.entra_client_secret,
        server_metadata_url=(
            f"https://login.microsoftonline.com/{settings.entra_tenant_id}"
            "/v2.0/.well-known/openid-configuration"
        ),
        client_kwargs={"scope": "openid email profile"},
        code_challenge_method="S256",
    )


def get_configured_providers() -> list[str]:
    providers = []
    if settings.google_client_id:
        providers.append("google")
    if settings.github_client_id:
        providers.append("github")
    if settings.entra_client_id and settings.entra_tenant_id:
        providers.append("entra_id")
    return providers
