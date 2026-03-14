"""Tests for cat_service: state transitions, groom, heal."""
from datetime import datetime, timezone, timedelta

import pytest
from app.services import cat_service
from app.models import Cat, _uuid, _utcnow


def _hours_ago(h: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=h)).isoformat()


@pytest.mark.asyncio
async def test_get_active_cat_creates_if_missing(db, user):
    cat = await cat_service.get_active_cat(db, user)
    assert cat is not None
    assert cat.language == user.target_language
    assert cat.state == "happy"


@pytest.mark.asyncio
async def test_get_active_cat_returns_none_without_language(db, user):
    user.target_language = None
    cat = await cat_service.get_active_cat(db, user)
    assert cat is None


@pytest.mark.asyncio
async def test_get_active_cat_returns_existing(db, user, cat):
    fetched = await cat_service.get_active_cat(db, user)
    assert fetched.id == cat.id


@pytest.mark.asyncio
async def test_update_state_happy_within_24h(db, user, cat):
    user.last_groomed_at = _hours_ago(12)
    result = await cat_service.update_state(db, cat, user)
    assert result.state == "happy"


@pytest.mark.asyncio
async def test_update_state_hangry_after_24h(db, user, cat):
    cat.state = "happy"
    user.last_groomed_at = _hours_ago(36)
    result = await cat_service.update_state(db, cat, user)
    assert result.state == "hangry"


@pytest.mark.asyncio
async def test_update_state_hospitalized_after_72h(db, user, cat):
    cat.state = "happy"
    user.last_groomed_at = _hours_ago(80)
    result = await cat_service.update_state(db, cat, user)
    assert result.state == "hospitalized"
    assert result.hospitalized_reason is not None


@pytest.mark.asyncio
async def test_update_state_no_op_without_groomed_at(db, user, cat):
    user.last_groomed_at = None
    result = await cat_service.update_state(db, cat, user)
    assert result.state == cat.state


@pytest.mark.asyncio
async def test_groom_sets_happy(db, user, cat):
    cat.state = "hangry"
    result = await cat_service.groom(db, cat, user)
    assert result.state == "happy"
    assert result.hospitalized_reason is None


@pytest.mark.asyncio
async def test_groom_increments_streak(db, user, cat):
    user.streak_days = 5
    await cat_service.groom(db, cat, user)
    assert user.streak_days == 6


@pytest.mark.asyncio
async def test_groom_sets_last_groomed_at(db, user, cat):
    user.last_groomed_at = None
    await cat_service.groom(db, cat, user)
    assert user.last_groomed_at is not None


@pytest.mark.asyncio
async def test_heal_hospitalized_cat(db, user, cat):
    cat.state = "hospitalized"
    cat.hospitalized_reason = "ate a cactus"
    result = await cat_service.heal(db, cat, user)
    assert result.state == "happy"
    assert result.hospitalized_reason is None


@pytest.mark.asyncio
async def test_heal_non_hospitalized_is_noop(db, user, cat):
    cat.state = "hangry"
    result = await cat_service.heal(db, cat, user)
    assert result.state == "hangry"
