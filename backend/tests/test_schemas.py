"""Tests for Pydantic schemas: validation and defaults."""
import pytest
from pydantic import ValidationError
from app.schemas import (
    GoalCreate, GoalResponse, GoalAction,
    CardResponse, CardUpdate, ReviewRequest,
    SubtitleImportResponse, UserUpdate,
)


# --- GoalCreate ---

def test_goal_create_minimal():
    g = GoalCreate(title="Naruto")
    assert g.title == "Naruto"
    assert g.media_type is None
    assert g.language is None


def test_goal_create_full():
    g = GoalCreate(title="Naruto", media_type="series", language="ja")
    assert g.media_type == "series"
    assert g.language == "ja"


def test_goal_create_missing_title_raises():
    with pytest.raises(ValidationError):
        GoalCreate()


# --- GoalAction ---

def test_goal_action_fields():
    a = GoalAction(id="import_subtitles", label="Import Vocab")
    assert a.id == "import_subtitles"
    assert a.label == "Import Vocab"


# --- GoalResponse ---

def test_goal_response_actions_default_empty():
    now = "2024-01-01T00:00:00+00:00"
    r = GoalResponse(
        id="g1", title="Test", language="es",
        status="active", created_at=now,
    )
    assert r.actions == []


def test_goal_response_with_actions():
    now = "2024-01-01T00:00:00+00:00"
    r = GoalResponse(
        id="g1", title="Test", language="es", status="active",
        created_at=now,
        actions=[GoalAction(id="import_subtitles", label="Import Vocab")],
    )
    assert len(r.actions) == 1
    assert r.actions[0].id == "import_subtitles"


# --- CardUpdate ---

def test_card_update_all_optional():
    u = CardUpdate()
    assert u.front is None
    assert u.back is None
    assert u.context_sentence is None


def test_card_update_partial():
    u = CardUpdate(front="new front")
    assert u.front == "new front"
    assert u.back is None


# --- ReviewRequest ---

def test_review_request_valid():
    r = ReviewRequest(rating=3)
    assert r.rating == 3


def test_review_request_missing_rating_raises():
    with pytest.raises(ValidationError):
        ReviewRequest()


# --- SubtitleImportResponse ---

def test_subtitle_import_response():
    r = SubtitleImportResponse(
        total_words=500, new_cards=42,
        existing_cards=10, subtitle_name="sub.srt",
    )
    assert r.new_cards == 42
    assert r.total_words == 500


# --- UserUpdate ---

def test_user_update_all_optional():
    u = UserUpdate()
    assert u.name is None
    assert u.target_language is None


def test_user_update_known_languages_list():
    u = UserUpdate(known_languages=["en", "fr"])
    assert u.known_languages == ["en", "fr"]
