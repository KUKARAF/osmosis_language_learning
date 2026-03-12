import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, _uuid, _utcnow


async def get_or_create_user(db: AsyncSession, oidc_claims: dict) -> User:
    """Find user by oidc_sub or create a new one."""
    sub = oidc_claims.get("sub")
    result = await db.execute(select(User).where(User.oidc_sub == sub))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(
        id=_uuid(),
        oidc_sub=sub,
        name=oidc_claims.get("name") or oidc_claims.get("preferred_username"),
        known_languages=json.dumps([]),
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
