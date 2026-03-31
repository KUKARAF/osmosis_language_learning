import re
from datetime import datetime, timezone

from fsrs import Scheduler, Card, Rating, State
from sqlalchemy import delete, select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Goal, SRSCard, SRSReviewLog, GoalWord, _uuid, _utcnow
from app import llm as app_llm

_POS_PLACEHOLDER = re.compile(r"^\[.+\]$")

_scheduler = Scheduler()

RATING_MAP = {1: Rating.Again, 2: Rating.Hard, 3: Rating.Good, 4: Rating.Easy}


def _card_from_db(db_card: SRSCard) -> Card:
    """Reconstruct a py-fsrs Card from DB fields."""
    card = Card()
    if db_card.fsrs_due:
        card.due = datetime.fromisoformat(db_card.fsrs_due)
    if db_card.fsrs_stability is not None:
        card.stability = db_card.fsrs_stability
    if db_card.fsrs_difficulty is not None:
        card.difficulty = db_card.fsrs_difficulty
    card.step = db_card.fsrs_reps  # fsrs v6 uses `step`
    if db_card.fsrs_last_review:
        card.last_review = datetime.fromisoformat(db_card.fsrs_last_review)
    card.state = State(db_card.fsrs_state) if db_card.fsrs_state in (1, 2, 3) else State.Learning
    return card


def _save_card_state(db_card: SRSCard, card: Card) -> None:
    """Write py-fsrs Card state back to DB model."""
    db_card.fsrs_stability = card.stability
    db_card.fsrs_difficulty = card.difficulty
    db_card.fsrs_due = card.due.isoformat() if card.due else None
    db_card.fsrs_last_review = card.last_review.isoformat() if card.last_review else None
    db_card.fsrs_reps = card.step if card.step is not None else 0
    db_card.fsrs_state = card.state.value if hasattr(card.state, "value") else int(card.state)


async def get_due_cards(
    db: AsyncSession, user_id: str, language: str | None = None, limit: int = 20
) -> list[SRSCard]:
    now = datetime.now(timezone.utc).isoformat()
    q = select(SRSCard).where(
        SRSCard.user_id == user_id,
        (SRSCard.fsrs_due <= now) | (SRSCard.fsrs_due.is_(None)),
    )
    if language:
        q = q.where(SRSCard.language == language)
    q = q.order_by(SRSCard.fsrs_due).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def review_card(
    db: AsyncSession, card_id: str, rating: int, source: str
) -> SRSCard:
    result = await db.execute(select(SRSCard).where(SRSCard.id == card_id))
    db_card = result.scalar_one_or_none()
    if db_card is None:
        raise ValueError(f"Card {card_id} not found")

    card = _card_from_db(db_card)
    fsrs_rating = RATING_MAP.get(rating, Rating.Good)
    updated_card, review_log = _scheduler.review_card(card, fsrs_rating)

    _save_card_state(db_card, updated_card)

    log = SRSReviewLog(
        id=_uuid(),
        card_id=card_id,
        rating=rating,
        source=source,
        review_at=_utcnow(),
    )
    db.add(log)
    await db.commit()
    await db.refresh(db_card)

    # Update known_words for any goals that contain this card
    goal_ids_result = await db.execute(
        select(GoalWord.goal_id).where(GoalWord.card_id == card_id)
    )
    goal_ids = [row.goal_id for row in goal_ids_result]
    for goal_id in goal_ids:
        known_count = (await db.execute(
            select(func.count(GoalWord.card_id))
            .join(SRSCard, SRSCard.id == GoalWord.card_id)
            .where(GoalWord.goal_id == goal_id, SRSCard.fsrs_state == 2)
        )).scalar() or 0
        await db.execute(
            update(Goal).where(Goal.id == goal_id).values(known_words=known_count)
        )
    if goal_ids:
        await db.commit()

    return db_card


async def find_or_create_card(
    db: AsyncSession,
    user_id: str,
    word: str,
    language: str,
    back: str,
    card_type: str = "vocabulary",
    context_sentence: str | None = None,
    source: str = "chat",
) -> SRSCard:
    result = await db.execute(
        select(SRSCard).where(
            SRSCard.user_id == user_id,
            SRSCard.front == word,
            SRSCard.language == language,
        )
    )
    card = result.scalar_one_or_none()
    if card is not None:
        return card

    now = _utcnow()
    card = SRSCard(
        id=_uuid(),
        user_id=user_id,
        card_type=card_type,
        front=word,
        back=back,
        context_sentence=context_sentence,
        language=language,
        fsrs_due=now,
        fsrs_state=0,
        source=source,
        created_at=now,
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return card


async def delete_card(db: AsyncSession, card_id: str, user_id: str) -> None:
    result = await db.execute(
        select(SRSCard).where(SRSCard.id == card_id, SRSCard.user_id == user_id)
    )
    db_card = result.scalar_one_or_none()
    if db_card is None:
        raise ValueError(f"Card {card_id} not found")
    await db.execute(
        delete(SRSReviewLog).where(SRSReviewLog.card_id == card_id)
    )
    await db.execute(
        delete(GoalWord).where(GoalWord.card_id == card_id)
    )
    await db.delete(db_card)
    await db.commit()


async def update_card(
    db: AsyncSession, card_id: str, user_id: str, updates: dict
) -> SRSCard:
    result = await db.execute(
        select(SRSCard).where(SRSCard.id == card_id, SRSCard.user_id == user_id)
    )
    db_card = result.scalar_one_or_none()
    if db_card is None:
        raise ValueError(f"Card {card_id} not found")
    for field, value in updates.items():
        if value is not None:
            setattr(db_card, field, value)
    await db.commit()
    await db.refresh(db_card)
    return db_card


async def delete_all_cards(db: AsyncSession, user_id: str) -> int:
    card_ids_q = select(SRSCard.id).where(SRSCard.user_id == user_id)
    card_ids = (await db.execute(card_ids_q)).scalars().all()
    if not card_ids:
        return 0
    await db.execute(
        delete(SRSReviewLog).where(SRSReviewLog.card_id.in_(card_ids))
    )
    await db.execute(
        delete(GoalWord).where(GoalWord.card_id.in_(card_ids))
    )
    await db.execute(
        delete(SRSCard).where(SRSCard.user_id == user_id)
    )
    await db.commit()
    return len(card_ids)


async def generate_card_back(
    db: AsyncSession, card_id: str, user_id: str, known_languages: list[str]
) -> SRSCard:
    result = await db.execute(
        select(SRSCard).where(SRSCard.id == card_id, SRSCard.user_id == user_id)
    )
    db_card = result.scalar_one_or_none()
    if db_card is None:
        raise ValueError(f"Card {card_id} not found")

    # Already has a real back — return as-is
    if db_card.back and not _POS_PLACEHOLDER.match(db_card.back):
        return db_card

    native = known_languages[0] if known_languages else "English"
    context_part = (
        f'\nContext sentence: "{db_card.context_sentence}"'
        if db_card.context_sentence
        else ""
    )
    prompt = (
        f"Translate the {db_card.language} word \"{db_card.front}\" into {native}. "
        f"Give only the concise translation, nothing else.{context_part}"
    )

    translation = await app_llm.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        model=app_llm.summarization_model(),
    )

    db_card.back = translation.strip()
    await db.commit()
    await db.refresh(db_card)
    return db_card


async def get_stats(
    db: AsyncSession, user_id: str, language: str | None = None
) -> dict:
    now = datetime.now(timezone.utc).isoformat()

    total_q = select(func.count(SRSCard.id)).where(SRSCard.user_id == user_id)
    due_q = select(func.count(SRSCard.id)).where(
        SRSCard.user_id == user_id,
        (SRSCard.fsrs_due <= now) | (SRSCard.fsrs_due.is_(None)),
    )
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).isoformat()
    reviews_q = select(func.count(SRSReviewLog.id)).where(
        SRSReviewLog.review_at >= today_start,
        SRSReviewLog.card_id.in_(
            select(SRSCard.id).where(SRSCard.user_id == user_id)
        ),
    )

    if language:
        total_q = total_q.where(SRSCard.language == language)
        due_q = due_q.where(SRSCard.language == language)

    total = (await db.execute(total_q)).scalar() or 0
    due = (await db.execute(due_q)).scalar() or 0
    reviews = (await db.execute(reviews_q)).scalar() or 0

    return {"total_cards": total, "due_today": due, "reviews_today": reviews}
