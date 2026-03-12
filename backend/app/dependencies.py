import json
from functools import lru_cache

from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, settings
from app.database import get_db
from app.models import User


@lru_cache
def get_settings() -> Settings:
    return settings


async def get_current_user(
    session: AsyncSession = Depends(get_db),
    app_settings: Settings = Depends(get_settings),
    session_token: str | None = Cookie(default=None),
) -> User:
    """Validate session cookie and return the current User."""
    if app_settings.DEV_MODE:
        return await _get_or_create_dev_user(session)

    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = jwt.decode(
            session_token, app_settings.SECRET_KEY, algorithms=["HS256"]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def _get_or_create_dev_user(session: AsyncSession) -> User:
    result = await session.execute(
        select(User).where(User.oidc_sub == "dev-user")
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            oidc_sub="dev-user",
            name="Dev User",
            known_languages=json.dumps(["en"]),
            target_language="es",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user
