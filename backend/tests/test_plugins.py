"""Tests for the plugin registry system."""
import pytest
from app import plugins
from app.plugins import goal_actions_for, goal_media_types


class _FakePlugin:
    name = "fake"
    version = "0.0.1"

    def get_tools(self): return []
    def get_tool_handlers(self): return {}
    def get_router(self): return None
    def get_media_types(self): return ["series", "movie", "book"]
    def get_goal_actions(self):
        return [
            {"media_types": ["series", "movie"], "id": "import_subtitles", "label": "Import Vocab"},
            {"media_types": ["book"], "id": "import_text", "label": "Import Text"},
        ]
    async def on_startup(self, app): pass


@pytest.fixture(autouse=True)
def isolated_registry():
    original = list(plugins._registry)
    plugins._registry = [_FakePlugin()]
    yield
    plugins._registry = original


def test_goal_media_types_from_plugin():
    types = goal_media_types()
    assert "series" in types
    assert "movie" in types
    assert "book" in types


def test_goal_media_types_sorted():
    types = goal_media_types()
    assert types == sorted(types)


def test_goal_actions_for_series():
    actions = goal_actions_for("series")
    ids = [a["id"] for a in actions]
    assert "import_subtitles" in ids


def test_goal_actions_for_movie():
    actions = goal_actions_for("movie")
    assert any(a["id"] == "import_subtitles" for a in actions)


def test_goal_actions_for_book():
    actions = goal_actions_for("book")
    assert any(a["id"] == "import_text" for a in actions)
    assert not any(a["id"] == "import_subtitles" for a in actions)


def test_goal_actions_for_unknown_type():
    actions = goal_actions_for("other")
    assert actions == []


def test_goal_actions_shape():
    actions = goal_actions_for("series")
    for a in actions:
        assert "id" in a
        assert "label" in a
        assert "media_types" not in a  # stripped in aggregator


def test_empty_registry_returns_empty():
    plugins._registry = []
    assert goal_media_types() == []
    assert goal_actions_for("series") == []
