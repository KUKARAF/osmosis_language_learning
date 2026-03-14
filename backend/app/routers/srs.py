from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import CardResponse, ReviewRequest, ReviewResponse, StatsResponse
from app.services import srs_service

router = APIRouter()


@router.get("/cards")
async def list_cards(
    language: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CardResponse]:
    cards = await srs_service.get_due_cards(db, user.id, language=language, limit=100)
    return [_card_response(c) for c in cards]


@router.get("/cards/due")
async def get_due_cards(
    language: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CardResponse]:
    cards = await srs_service.get_due_cards(db, user.id, language=language, limit=limit)
    return [_card_response(c) for c in cards]


@router.post("/cards/{card_id}/review")
async def review_card(
    card_id: str,
    body: ReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    if body.rating not in (1, 2, 3, 4):
        raise HTTPException(status_code=400, detail="Rating must be 1-4")
    try:
        card = await srs_service.review_card(
            db, card_id, body.rating, source="flashcard_manual"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ReviewResponse(
        card=_card_response(card),
        next_review=card.fsrs_due,
        scheduled_days=None,
    )


@router.delete("/cards/{card_id}", status_code=204)
async def delete_card(
    card_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await srs_service.delete_card(db, card_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return Response(status_code=204)


@router.get("/stats")
async def get_stats(
    language: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatsResponse:
    stats = await srs_service.get_stats(db, user.id, language=language)
    return StatsResponse(
        total_cards=stats["total_cards"],
        due_today=stats["due_today"],
        reviews_today=stats["reviews_today"],
        streak_days=user.streak_days,
    )


def _card_response(c) -> CardResponse:
    return CardResponse(
        id=c.id, card_type=c.card_type, front=c.front, back=c.back,
        context_sentence=c.context_sentence, language=c.language,
        fsrs_stability=c.fsrs_stability, fsrs_difficulty=c.fsrs_difficulty,
        fsrs_due=c.fsrs_due, fsrs_reps=c.fsrs_reps, fsrs_lapses=c.fsrs_lapses,
        fsrs_state=c.fsrs_state, source=c.source, created_at=c.created_at,
    )
