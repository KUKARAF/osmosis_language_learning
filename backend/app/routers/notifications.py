from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import NotificationResponse
from app.services import notification_service

router = APIRouter()


@router.get("")
async def list_notifications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationResponse]:
    notifs = await notification_service.get_all(db, user.id)
    return [
        NotificationResponse(
            id=n.id, type=n.type, title=n.title, body=n.body,
            read=bool(n.read), created_at=n.created_at,
        )
        for n in notifs
    ]


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await notification_service.mark_read(db, notification_id)
    return {"status": "ok"}


@router.post("/read-all")
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await notification_service.mark_all_read(db, user.id)
    return {"status": "ok"}
