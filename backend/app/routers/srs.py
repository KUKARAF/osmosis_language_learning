import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import CardResponse, CardUpdate, ReviewRequest, ReviewResponse, StatsResponse
from app.services import srs_service
from app import llm as app_llm
from app.llm.prompt_loader import registry as prompt_registry


class SpeakRequest(BaseModel):
    text: str
    voice: str = "alloy"


class EvaluateRequest(BaseModel):
    user_answer: str
    card_prompt: str
    correct_answer: str


class EvaluateResponse(BaseModel):
    rating: int
    explanation: str

router = APIRouter()


@router.get("/cards")
async def list_cards(
    language: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CardResponse]:
    cards = await srs_service.get_due_cards(db, user.id, language=language, limit=100)
    return [_card_response(c) for c in cards]


@router.get("/cards/due")
async def get_due_cards(
    language: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CardResponse]:
    cards = await srs_service.get_due_cards(db, user.id, language=language, limit=limit)
    return [_card_response(c) for c in cards]


@router.post("/cards/{card_id}/review")
async def review_card(
    card_id: str,
    body: ReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    if body.rating not in (1, 2, 3, 4):
        raise HTTPException(status_code=400, detail="Rating must be 1-4")
    try:
        card = await srs_service.review_card(
            db, card_id, body.rating, source="flashcard_manual"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ReviewResponse(
        card=_card_response(card),
        next_review=card.fsrs_due,
        scheduled_days=None,
    )


@router.post("/cards/{card_id}/generate-back")
async def generate_back(
    card_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CardResponse:
    import json
    known = json.loads(user.known_languages) if user.known_languages else []
    try:
        card = await srs_service.generate_card_back(db, card_id, user.id, known)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _card_response(card)


@router.post("/cards/{card_id}/speak")
async def speak_text(
    card_id: str,
    body: SpeakRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Synthesize speech using Groq PlayAI TTS. Returns mp3 audio."""
    try:
        audio_bytes = await app_llm.speak(body.text, voice=body.voice)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TTS failed: {exc}") from exc

    import io
    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-store"},
    )


@router.post("/cards/{card_id}/transcribe")
async def transcribe_audio(
    card_id: str,
    audio: UploadFile = File(...),
    language: str = Form("en"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Transcribe a recorded answer using Groq Whisper STT."""
    audio_bytes = await audio.read()
    try:
        text = await app_llm.transcribe_audio(
            audio_bytes, audio.filename or "recording.webm", language
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}") from exc
    return {"text": text}


@router.post("/cards/{card_id}/evaluate")
async def evaluate_answer(
    card_id: str,
    body: EvaluateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EvaluateResponse:
    """Evaluate a learner's typed/spoken answer against the correct answer."""
    meta, prompt_body = prompt_registry.render(
        "card_evaluation",
        card_prompt=body.card_prompt,
        correct_answer=body.correct_answer,
        user_answer=body.user_answer,
    )
    model = meta.get("model", app_llm.summarization_model())
    try:
        raw = await app_llm.chat_completion(
            messages=[{"role": "user", "content": prompt_body}],
            model=model,
            temperature=float(meta.get("temperature", 0.2)),
            response_format={"type": "json_object"},
        )
        data = json.loads(raw)
        return EvaluateResponse(
            rating=int(data["rating"]),
            explanation=data["explanation"],
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Evaluation failed: {exc}") from exc


@router.patch("/cards/{card_id}")
async def update_card(
    card_id: str,
    body: CardUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CardResponse:
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        card = await srs_service.update_card(db, card_id, user.id, updates)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _card_response(card)


@router.delete("/cards", status_code=204)
async def delete_all_cards(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    if not settings.DEV_MODE:
        raise HTTPException(status_code=403, detail="Only available in dev mode")
    await srs_service.delete_all_cards(db, user.id)
    return Response(status_code=204)


@router.delete("/cards/{card_id}", status_code=204)
async def delete_card(
    card_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await srs_service.delete_card(db, card_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return Response(status_code=204)


@router.get("/words")
async def get_word_states(
    language: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return all card fronts with their SRS state (lightweight, for word highlighting)."""
    return await srs_service.get_all_card_fronts(db, user.id, language=language)


@router.get("/stats")
async def get_stats(
    language: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatsResponse:
    stats = await srs_service.get_stats(db, user.id, language=language)
    return StatsResponse(
        total_cards=stats["total_cards"],
        due_today=stats["due_today"],
        reviews_today=stats["reviews_today"],
        streak_days=user.streak_days,
    )


def _card_response(c) -> CardResponse:
    return CardResponse(
        id=c.id, card_type=c.card_type, front=c.front, back=c.back,
        context_sentence=c.context_sentence, language=c.language,
        fsrs_stability=c.fsrs_stability, fsrs_difficulty=c.fsrs_difficulty,
        fsrs_due=c.fsrs_due, fsrs_reps=c.fsrs_reps, fsrs_lapses=c.fsrs_lapses,
        fsrs_state=c.fsrs_state, source=c.source, created_at=c.created_at,
    )
