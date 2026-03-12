import json

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, _utcnow
from app.schemas import UserUpdate, UserResponse

router = APIRouter()


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    known = json.loads(user.known_languages) if user.known_languages else []
    return UserResponse(
        id=user.id, name=user.name, known_languages=known,
        target_language=user.target_language, streak_days=user.streak_days,
        payment_path=user.payment_path, created_at=user.created_at,
    )


@router.patch("/me")
async def update_me(
    body: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    if body.name is not None:
        user.name = body.name
    if body.known_languages is not None:
        user.known_languages = json.dumps(body.known_languages)
    if body.target_language is not None:
        user.target_language = body.target_language
    user.updated_at = _utcnow()
    await db.commit()
    await db.refresh(user)
    known = json.loads(user.known_languages) if user.known_languages else []
    return UserResponse(
        id=user.id, name=user.name, known_languages=known,
        target_language=user.target_language, streak_days=user.streak_days,
        payment_path=user.payment_path, created_at=user.created_at,
    )
