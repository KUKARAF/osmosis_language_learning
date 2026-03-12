from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Goal, _uuid, _utcnow


async def create_goal(
    db: AsyncSession,
    user_id: str,
    title: str,
    language: str,
    media_type: str | None = None,
) -> Goal:
    goal = Goal(
        id=_uuid(),
        user_id=user_id,
        title=title,
        media_type=media_type,
        language=language,
        created_at=_utcnow(),
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal


async def get_goals(db: AsyncSession, user_id: str) -> list[Goal]:
    result = await db.execute(
        select(Goal).where(Goal.user_id == user_id).order_by(Goal.created_at.desc())
    )
    return list(result.scalars().all())


async def get_goal(db: AsyncSession, goal_id: str) -> Goal | None:
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    return result.scalar_one_or_none()
