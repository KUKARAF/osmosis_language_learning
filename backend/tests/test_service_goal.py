"""Tests for goal_service: CRUD operations."""
import pytest
from app.services import goal_service


@pytest.mark.asyncio
async def test_create_goal(db, user):
    goal = await goal_service.create_goal(
        db, user_id=user.id, title="Breaking Bad",
        language="es", media_type="series",
    )
    assert goal.id is not None
    assert goal.title == "Breaking Bad"
    assert goal.language == "es"
    assert goal.media_type == "series"
    assert goal.status == "active"


@pytest.mark.asyncio
async def test_create_goal_no_media_type(db, user):
    goal = await goal_service.create_goal(
        db, user_id=user.id, title="Something",
        language="fr", media_type=None,
    )
    assert goal.media_type is None


@pytest.mark.asyncio
async def test_get_goal_returns_correct(db, user, goal):
    fetched = await goal_service.get_goal(db, goal.id)
    assert fetched is not None
    assert fetched.id == goal.id
    assert fetched.title == goal.title


@pytest.mark.asyncio
async def test_get_goal_unknown_returns_none(db):
    result = await goal_service.get_goal(db, "nonexistent-id")
    assert result is None


@pytest.mark.asyncio
async def test_get_goals_lists_user_goals(db, user):
    await goal_service.create_goal(db, user_id=user.id, title="A", language="es")
    await goal_service.create_goal(db, user_id=user.id, title="B", language="es")
    goals = await goal_service.get_goals(db, user.id)
    titles = [g.title for g in goals]
    assert "A" in titles
    assert "B" in titles


@pytest.mark.asyncio
async def test_get_goals_sorted_newest_first(db, user):
    await goal_service.create_goal(db, user_id=user.id, title="First", language="es")
    await goal_service.create_goal(db, user_id=user.id, title="Second", language="es")
    goals = await goal_service.get_goals(db, user.id)
    assert goals[0].title == "Second"


@pytest.mark.asyncio
async def test_get_goals_empty_for_new_user(db, user):
    goals = await goal_service.get_goals(db, "other-user-id")
    assert goals == []
