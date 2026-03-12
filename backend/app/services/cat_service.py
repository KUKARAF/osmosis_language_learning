import random
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Cat, User, _uuid, _utcnow

HOSPITALIZED_REASONS = [
    "tried to eat a fish-shaped plastic toy and got it stuck in its throat",
    "fell off a dumpster while chasing a pigeon and broke three whiskers",
    "ate some suspicious sushi from behind a Japanese restaurant and regretted everything",
    "got into a fight with a raccoon over a leftover burrito",
    "swallowed a rubber band thinking it was a snake and needed emergency surgery",
    "tried to befriend a cactus and ended up looking like a pincushion",
    "drank from a puddle of espresso and vibrated for 48 hours straight",
    "ate an entire wheel of aged cheese and couldn't move for three days",
]


async def get_active_cat(db: AsyncSession, user: User) -> Cat | None:
    """Get cat for the user's current target_language. Create if needed."""
    if not user.target_language:
        return None

    result = await db.execute(
        select(Cat).where(
            Cat.user_id == user.id, Cat.language == user.target_language
        )
    )
    cat = result.scalar_one_or_none()
    if cat is None:
        cat = Cat(
            id=_uuid(),
            user_id=user.id,
            language=user.target_language,
            state="happy",
            created_at=_utcnow(),
        )
        db.add(cat)
        await db.commit()
        await db.refresh(cat)
    else:
        cat = await update_state(db, cat, user)
    return cat


async def groom(db: AsyncSession, cat: Cat, user: User) -> Cat:
    """Groom the cat: update state, reset streak timer."""
    now = _utcnow()
    user.last_groomed_at = now
    user.streak_days = user.streak_days + 1
    user.updated_at = now
    cat.state = "happy"
    cat.hospitalized_reason = None
    await db.commit()
    await db.refresh(cat)
    await db.refresh(user)
    return cat


async def update_state(db: AsyncSession, cat: Cat, user: User) -> Cat:
    """Check last_groomed_at and transition state."""
    if user.last_groomed_at is None:
        return cat

    last = datetime.fromisoformat(user.last_groomed_at)
    now = datetime.now(timezone.utc)
    hours_since = (now - last).total_seconds() / 3600

    if hours_since < 24:
        new_state = "happy"
    elif hours_since < 72:
        new_state = "hangry"
    else:
        new_state = "hospitalized"

    if new_state != cat.state:
        cat.state = new_state
        if new_state == "hospitalized" and not cat.hospitalized_reason:
            cat.hospitalized_reason = random.choice(HOSPITALIZED_REASONS)
        elif new_state != "hospitalized":
            cat.hospitalized_reason = None
        await db.commit()
        await db.refresh(cat)

    return cat


async def heal(db: AsyncSession, cat: Cat, user: User) -> Cat:
    """Heal a hospitalized cat."""
    if cat.state != "hospitalized":
        return cat
    cat.state = "happy"
    cat.hospitalized_reason = None
    user.last_groomed_at = _utcnow()
    user.updated_at = _utcnow()
    await db.commit()
    await db.refresh(cat)
    return cat
