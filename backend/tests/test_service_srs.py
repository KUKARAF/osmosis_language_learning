"""Tests for srs_service: cards, reviews, stats."""
import pytest
from app.services import srs_service
from app.models import SRSCard, _uuid, _utcnow


@pytest.mark.asyncio
async def test_find_or_create_card_creates(db, user):
    card = await srs_service.find_or_create_card(
        db, user_id=user.id, word="perro", language="es", back="dog",
    )
    assert card.id is not None
    assert card.front == "perro"
    assert card.back == "dog"
    assert card.language == "es"


@pytest.mark.asyncio
async def test_find_or_create_card_idempotent(db, user):
    c1 = await srs_service.find_or_create_card(
        db, user_id=user.id, word="gato", language="es", back="cat",
    )
    c2 = await srs_service.find_or_create_card(
        db, user_id=user.id, word="gato", language="es", back="cat",
    )
    assert c1.id == c2.id


@pytest.mark.asyncio
async def test_review_card_updates_fsrs_state(db, user, card):
    reviewed = await srs_service.review_card(db, card.id, rating=3, source="test")
    assert reviewed.fsrs_state != 0 or reviewed.fsrs_stability is not None


@pytest.mark.asyncio
async def test_review_card_not_found_raises(db):
    with pytest.raises(ValueError, match="not found"):
        await srs_service.review_card(db, "bad-id", rating=3, source="test")


@pytest.mark.asyncio
async def test_get_due_cards_includes_new_card(db, user, card):
    due = await srs_service.get_due_cards(db, user.id)
    ids = [c.id for c in due]
    assert card.id in ids


@pytest.mark.asyncio
async def test_get_due_cards_language_filter(db, user, card):
    # card is "es" — filtering for "ja" should exclude it
    due = await srs_service.get_due_cards(db, user.id, language="ja")
    assert all(c.language == "ja" for c in due)


@pytest.mark.asyncio
async def test_update_card_changes_fields(db, user, card):
    updated = await srs_service.update_card(
        db, card.id, user.id, {"front": "gato updated", "back": "cat updated"}
    )
    assert updated.front == "gato updated"
    assert updated.back == "cat updated"


@pytest.mark.asyncio
async def test_update_card_not_found_raises(db, user):
    with pytest.raises(ValueError, match="not found"):
        await srs_service.update_card(db, "bad-id", user.id, {"front": "x"})


@pytest.mark.asyncio
async def test_delete_card_removes_it(db, user, card):
    await srs_service.delete_card(db, card.id, user.id)
    due = await srs_service.get_due_cards(db, user.id)
    assert all(c.id != card.id for c in due)


@pytest.mark.asyncio
async def test_delete_card_not_found_raises(db, user):
    with pytest.raises(ValueError, match="not found"):
        await srs_service.delete_card(db, "bad-id", user.id)


@pytest.mark.asyncio
async def test_delete_all_cards(db, user):
    await srs_service.find_or_create_card(db, user.id, "uno", "es", "one")
    await srs_service.find_or_create_card(db, user.id, "dos", "es", "two")
    count = await srs_service.delete_all_cards(db, user.id)
    assert count >= 2
    due = await srs_service.get_due_cards(db, user.id)
    assert due == []


@pytest.mark.asyncio
async def test_get_stats_counts_total(db, user):
    await srs_service.find_or_create_card(db, user.id, "tres", "es", "three")
    stats = await srs_service.get_stats(db, user.id)
    assert stats["total_cards"] >= 1
    assert "due_today" in stats
    assert "reviews_today" in stats


@pytest.mark.asyncio
async def test_get_stats_empty_for_new_user(db):
    stats = await srs_service.get_stats(db, "no-user")
    assert stats["total_cards"] == 0
    assert stats["due_today"] == 0


def test_card_from_db_reconstructs():
    now = _utcnow()
    db_card = SRSCard(
        id=_uuid(), user_id="u", card_type="vocabulary",
        front="x", back="y", language="es",
        fsrs_due=now, fsrs_state=1, fsrs_reps=2,
        fsrs_stability=3.5, fsrs_difficulty=5.0,
        source="chat", created_at=now,
    )
    card = srs_service._card_from_db(db_card)
    assert card.stability == 3.5
    assert card.difficulty == 5.0
    assert card.step == 2
