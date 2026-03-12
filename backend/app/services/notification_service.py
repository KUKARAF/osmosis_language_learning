from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, _uuid, _utcnow


async def create(
    db: AsyncSession, user_id: str, type: str, title: str, body: str = ""
) -> Notification:
    n = Notification(
        id=_uuid(),
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        created_at=_utcnow(),
    )
    db.add(n)
    await db.commit()
    await db.refresh(n)
    return n


async def get_unread(db: AsyncSession, user_id: str) -> list[Notification]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id, Notification.read == 0)
        .order_by(Notification.created_at.desc())
    )
    return list(result.scalars().all())


async def get_all(db: AsyncSession, user_id: str) -> list[Notification]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.read, Notification.created_at.desc())
    )
    return list(result.scalars().all())


async def mark_read(db: AsyncSession, notification_id: str) -> None:
    await db.execute(
        update(Notification)
        .where(Notification.id == notification_id)
        .values(read=1)
    )
    await db.commit()


async def mark_all_read(db: AsyncSession, user_id: str) -> None:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.read == 0)
        .values(read=1)
    )
    await db.commit()
