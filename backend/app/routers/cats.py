from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Cat
from app.schemas import CatResponse, GroomResponse
from app.services import cat_service

router = APIRouter()


@router.get("")
async def list_cats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CatResponse]:
    result = await db.execute(select(Cat).where(Cat.user_id == user.id))
    return [
        CatResponse(
            id=c.id, language=c.language, name=c.name,
            state=c.state, hospitalized_reason=c.hospitalized_reason,
            created_at=c.created_at,
        )
        for c in result.scalars().all()
    ]


@router.get("/active")
async def get_active_cat(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CatResponse:
    cat = await cat_service.get_active_cat(db, user)
    if cat is None:
        raise HTTPException(status_code=404, detail="No active cat. Set a target language first.")
    return CatResponse(
        id=cat.id, language=cat.language, name=cat.name,
        state=cat.state, hospitalized_reason=cat.hospitalized_reason,
        created_at=cat.created_at,
    )


@router.post("/active/groom")
async def groom_cat(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroomResponse:
    cat = await cat_service.get_active_cat(db, user)
    if cat is None:
        raise HTTPException(status_code=404, detail="No active cat")
    cat = await cat_service.groom(db, cat, user)
    return GroomResponse(
        cat=CatResponse(
            id=cat.id, language=cat.language, name=cat.name,
            state=cat.state, hospitalized_reason=cat.hospitalized_reason,
            created_at=cat.created_at,
        ),
        message="*purrs contentedly*",
    )


@router.post("/active/heal")
async def heal_cat(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroomResponse:
    cat = await cat_service.get_active_cat(db, user)
    if cat is None:
        raise HTTPException(status_code=404, detail="No active cat")
    if cat.state != "hospitalized":
        raise HTTPException(status_code=400, detail="Cat is not hospitalized")
    cat = await cat_service.heal(db, cat, user)
    return GroomResponse(
        cat=CatResponse(
            id=cat.id, language=cat.language, name=cat.name,
            state=cat.state, hospitalized_reason=cat.hospitalized_reason,
            created_at=cat.created_at,
        ),
        message="*slowly opens one eye* ...I lived, but barely.",
    )
