import hashlib
import base64
import secrets

from fastapi import APIRouter, Depends, Response, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_authorize_url, exchange_code, get_userinfo, create_session_token, generate_state
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import UserInfo
from app.services.auth_service import get_or_create_user

router = APIRouter()

# In-memory PKCE store (fine for single-instance MVP)
# Maps state → (code_verifier, redirect_uri)
_pkce_store: dict[str, tuple[str, str | None]] = {}


@router.get("/login")
async def login(redirect_uri: str | None = None):
    """Redirect to OIDC provider."""
    if settings.DEV_MODE:
        return RedirectResponse("/")

    state = generate_state()
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    _pkce_store[state] = (code_verifier, redirect_uri)
    url = await get_authorize_url(state, code_challenge)
    return RedirectResponse(url)


@router.get("/callback")
async def callback(
    code: str,
    state: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """OIDC callback — exchange code, create session."""
    state_data = _pkce_store.pop(state, None)
    if state_data is None:
        return Response(status_code=400, content="Invalid state")

    code_verifier, redirect_uri = state_data
    tokens = await exchange_code(code, code_verifier)
    userinfo = await get_userinfo(tokens["access_token"])
    user = await get_or_create_user(db, userinfo)

    session_token = create_session_token(user.id)
    
    # Determine redirect target
    redirect_target = redirect_uri if redirect_uri else "/"
    
    # For mobile deep links, pass token as query parameter
    # For web, use cookie-based session
    if redirect_uri and redirect_uri.startswith(("osmosis://", "http://", "https://")):
        # Mobile app or external redirect - pass token in URL
        resp = RedirectResponse(f"{redirect_target}?token={session_token}")
    else:
        # Web app - use cookie-based session
        resp = RedirectResponse(redirect_target)
        resp.set_cookie(
            "session_token",
            session_token,
            httponly=True,
            samesite="lax",
            max_age=86400,
        )
    return resp


@router.post("/logout")
async def logout(response: Response):
    resp = Response(status_code=200)
    resp.delete_cookie("session_token")
    return resp


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> UserInfo:
    import json
    known = json.loads(user.known_languages) if user.known_languages else []
    return UserInfo(
        id=user.id,
        name=user.name,
        known_languages=known,
        target_language=user.target_language,
        streak_days=user.streak_days,
        dev_mode=settings.DEV_MODE,
    )
