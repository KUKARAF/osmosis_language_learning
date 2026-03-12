import secrets
from datetime import datetime, timezone, timedelta

import httpx
from jose import jwt

from app.config import settings

_oidc_config_cache: dict | None = None


async def get_oidc_config() -> dict:
    """Fetch and cache the OIDC discovery document."""
    global _oidc_config_cache
    if _oidc_config_cache is not None:
        return _oidc_config_cache
    url = settings.OIDC_ISSUER.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        _oidc_config_cache = resp.json()
        return _oidc_config_cache


async def get_authorize_url(state: str, code_challenge: str) -> str:
    """Build the OIDC authorize redirect URL."""
    oidc = await get_oidc_config()
    params = {
        "response_type": "code",
        "client_id": settings.OIDC_CLIENT_ID,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "scope": "openid profile email",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{oidc['authorization_endpoint']}?{qs}"


async def exchange_code(code: str, code_verifier: str) -> dict:
    """Exchange authorization code for tokens."""
    oidc = await get_oidc_config()
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "client_id": settings.OIDC_CLIENT_ID,
        "code_verifier": code_verifier,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(oidc["token_endpoint"], data=data)
        resp.raise_for_status()
        return resp.json()


async def get_userinfo(access_token: str) -> dict:
    """Fetch user info from OIDC provider."""
    oidc = await get_oidc_config()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            oidc["userinfo_endpoint"],
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()


def create_session_token(user_id: str) -> str:
    """Create a short-lived JWT for session management."""
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def generate_state() -> str:
    return secrets.token_urlsafe(32)
