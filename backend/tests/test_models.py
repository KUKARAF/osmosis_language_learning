"""Tests for model helpers and basic ORM field defaults."""
import re
import uuid
from datetime import timezone

import pytest
from app.models import _uuid, _utcnow, User, Cat, SRSCard, Goal


def test_uuid_is_valid_uuid4():
    val = _uuid()
    parsed = uuid.UUID(val)
    assert parsed.version == 4


def test_uuid_unique():
    assert _uuid() != _uuid()


def test_utcnow_is_iso_string():
    val = _utcnow()
    # ISO 8601 with timezone offset or Z
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", val)


def test_utcnow_contains_timezone():
    val = _utcnow()
    assert "+" in val or val.endswith("Z")


@pytest.mark.asyncio
async def test_user_persisted(db):
    u = User(
        id=_uuid(), oidc_sub="sub-xyz", name="Alice",
        known_languages='["en"]', target_language="fr",
        streak_days=3, created_at=_utcnow(), updated_at=_utcnow(),
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    assert u.id is not None
    assert u.name == "Alice"
    assert u.streak_days == 3


@pytest.mark.asyncio
async def test_cat_default_state(db, user):
    c = Cat(id=_uuid(), user_id=user.id, language="es", created_at=_utcnow())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    assert c.state == "happy"
    assert c.hospitalized_reason is None


@pytest.mark.asyncio
async def test_srs_card_defaults(db, user):
    now = _utcnow()
    card = SRSCard(
        id=_uuid(), user_id=user.id, card_type="vocabulary",
        front="perro", back="dog", language="es",
        fsrs_due=now, fsrs_state=0, fsrs_reps=0,
        source="chat", created_at=now,
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)
    assert card.fsrs_reps == 0
    assert card.fsrs_state == 0
    assert card.fsrs_lapses == 0


@pytest.mark.asyncio
async def test_goal_default_status(db, user):
    g = Goal(
        id=_uuid(), user_id=user.id, title="Naruto",
        language="ja", created_at=_utcnow(),
    )
    db.add(g)
    await db.commit()
    await db.refresh(g)
    assert g.status == "active"
