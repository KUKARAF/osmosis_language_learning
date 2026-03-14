"""Tests for goal_import_service: _clean_title and import_from_srt."""
import pytest
from app.services.goal_import_service import _clean_title, import_from_srt

SRT_ES = """\
1
00:00:01,000 --> 00:00:03,000
El detective encontró las pistas en el lugar.

2
00:00:04,000 --> 00:00:06,000
Ella corrió hacia la salida rápidamente.

3
00:00:07,000 --> 00:00:09,000
Los sospechosos huyeron del edificio oscuro.
"""


# --- _clean_title ---

@pytest.mark.parametrize("raw,expected", [
    ("Watch Breaking Bad", "Breaking Bad"),
    ("watch breaking bad", "breaking bad"),
    ("Read Don Quixote", "Don Quixote"),
    ("Study Naruto in Japanese", "Naruto"),
    ("La Casa de Papel", "La Casa de Papel"),
    ("Breaking Bad with Spanish subtitles", "Breaking Bad"),
    ("Learn from Spirited Away", "Spirited Away"),
    ("See The Office in English", "The Office"),
])
def test_clean_title(raw, expected):
    assert _clean_title(raw) == expected


# --- import_from_srt ---

@pytest.mark.asyncio
async def test_import_from_srt_creates_cards(db, user, goal):
    result = await import_from_srt(db, goal, srt_content=SRT_ES)
    assert result["new_cards"] > 0


@pytest.mark.asyncio
async def test_import_from_srt_returns_word_count(db, user, goal):
    result = await import_from_srt(db, goal, srt_content=SRT_ES)
    assert result["total_words"] > 0


@pytest.mark.asyncio
async def test_import_from_srt_idempotent_existing_cards(db, user, goal):
    r1 = await import_from_srt(db, goal, srt_content=SRT_ES)
    r2 = await import_from_srt(db, goal, srt_content=SRT_ES)
    # Second import: new_cards should be 0 (all already exist)
    assert r2["new_cards"] == 0
    assert r2["existing_cards"] == r1["new_cards"]


@pytest.mark.asyncio
async def test_import_from_srt_stores_srt_on_goal(db, user, goal):
    await import_from_srt(db, goal, srt_content=SRT_ES)
    await db.refresh(goal)
    assert goal.srt_content == SRT_ES


@pytest.mark.asyncio
async def test_import_from_srt_empty_raises(db, user, goal):
    # Empty SRT raises either ValueError (no vocabulary) or pysubs2 format error
    import pysubs2
    with pytest.raises((ValueError, pysubs2.exceptions.FormatAutodetectionError)):
        await import_from_srt(db, goal, srt_content="")
