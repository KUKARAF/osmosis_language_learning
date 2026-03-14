"""Shared fixtures: in-memory async SQLite DB, user, cat, card, goal."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import Base, User, Cat, Goal, SRSCard, _uuid, _utcnow


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def user(db):
    now = _utcnow()
    u = User(
        id=_uuid(),
        oidc_sub="test-sub-001",
        name="Test User",
        known_languages='["en"]',
        target_language="es",
        streak_days=0,
        created_at=now,
        updated_at=now,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest_asyncio.fixture
async def cat(db, user):
    now = _utcnow()
    c = Cat(
        id=_uuid(),
        user_id=user.id,
        language="es",
        state="happy",
        created_at=now,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@pytest_asyncio.fixture
async def card(db, user):
    now = _utcnow()
    c = SRSCard(
        id=_uuid(),
        user_id=user.id,
        card_type="vocabulary",
        front="gato",
        back="cat",
        language="es",
        fsrs_due=now,
        fsrs_state=0,
        fsrs_reps=0,
        source="chat",
        created_at=now,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@pytest_asyncio.fixture
async def goal(db, user):
    now = _utcnow()
    g = Goal(
        id=_uuid(),
        user_id=user.id,
        title="La Casa de Papel",
        media_type="series",
        language="es",
        status="active",
        created_at=now,
    )
    db.add(g)
    await db.commit()
    await db.refresh(g)
    return g
