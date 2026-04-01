import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from osmosis_media import fetch_and_process, process_srt
from osmosis_media.providers.subdl import SubDLProvider
from osmosis_ebook import process_ebook

from app.models import Goal, GoalWord, SRSCard, _uuid, _utcnow

_TITLE_NOISE = re.compile(
    r"^(watch|read|study|see|learn from|listen to)\s+",
    re.IGNORECASE,
)
_LANG_SUFFIX = re.compile(
    r"\s+(in\s+\w+|with\s+(spanish|english|french|german|japanese|portuguese|italian|korean|chinese|arabic|russian)\s*(subtitles?|audio|dub)?)$",
    re.IGNORECASE,
)


def _clean_title(title: str) -> str:
    t = _TITLE_NOISE.sub("", title.strip())
    t = _LANG_SUFFIX.sub("", t).strip()
    return t


async def import_from_srt(
    db: AsyncSession,
    goal: Goal,
    srt_content: str,
    source_url: str | None = None,
) -> dict:
    """Process a raw SRT string and import vocabulary into the goal."""
    media_goal = process_srt(
        srt=srt_content,
        language=goal.language,
        title=goal.title,
        media_type=goal.media_type or "other",
        source_url=source_url,
    )
    return await _persist(db, goal, media_goal, srt_content)


async def import_from_ebook(
    db: AsyncSession,
    goal: Goal,
    file_data: bytes,
    filename: str,
) -> dict:
    """Process an ebook file and import vocabulary into the goal."""
    media_goal = await process_ebook(
        data=file_data,
        filename=filename,
        language=goal.language,
        title=goal.title,
        media_type=goal.media_type or "book",
    )
    return await _persist(db, goal, media_goal, None)


async def auto_import(
    db: AsyncSession,
    goal: Goal,
    season: int | None = None,
    episode: int | None = None,
) -> dict:
    """Fetch subtitle via SubDL, process with NLP, import into goal."""
    media_goal = await fetch_and_process(
        title=_clean_title(goal.title),
        language=goal.language,
        season=season,
        episode=episode,
        media_type=goal.media_type or "series",
    )
    return await _persist(db, goal, media_goal, media_goal.raw_srt)


async def _persist(db: AsyncSession, goal: Goal, media_goal, srt_content: str | None) -> dict:
    """Bulk-insert SRS cards for each lemma and link them to the goal."""
    words = media_goal.words  # list[osmosis_media.Word]

    if not words:
        raise ValueError("No vocabulary could be extracted from the subtitle")

    lemmas = [w.lemma for w in words]

    # Fetch cards that already exist for this user+language in one query
    existing_result = await db.execute(
        select(SRSCard.front, SRSCard.id).where(
            SRSCard.user_id == goal.user_id,
            SRSCard.language == goal.language,
            SRSCard.front.in_(lemmas),
        )
    )
    existing: dict[str, str] = {row.front: row.id for row in existing_result}

    now = _utcnow()
    new_card_map: dict[str, str] = {}
    for word in words:
        if word.lemma not in existing:
            card_id = _uuid()
            db.add(SRSCard(
                id=card_id,
                user_id=goal.user_id,
                card_type="vocabulary",
                front=word.lemma,
                back="",
                context_sentence=word.example,
                language=goal.language,
                fsrs_due=now,
                fsrs_state=0,
                source="goal_import",
                created_at=now,
            ))
            new_card_map[word.lemma] = card_id

    await db.flush()

    all_card_ids = {**existing, **new_card_map}

    # Fetch existing GoalWord links
    existing_links_result = await db.execute(
        select(GoalWord.card_id).where(GoalWord.goal_id == goal.id)
    )
    existing_link_ids = {row.card_id for row in existing_links_result}

    for card_id in all_card_ids.values():
        if card_id not in existing_link_ids:
            db.add(GoalWord(goal_id=goal.id, card_id=card_id, added_at=now))

    goal.srt_content = srt_content
    goal.total_words = media_goal.word_count
    # unique_lemmas stored as total_words isn't great — let's store lemma count
    goal.known_words = 0  # reset; will be updated as user reviews

    await db.commit()

    return {
        "total_words": media_goal.word_count,
        "unique_lemmas": media_goal.unique_lemmas,
        "new_cards": len(new_card_map),
        "existing_cards": len(existing),
        "subtitle_name": getattr(media_goal, "source_url", "") or "",
    }
