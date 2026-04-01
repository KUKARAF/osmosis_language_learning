import base64
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import SRSCard, User
from app import llm as app_llm
from app.services import srs_service

router = APIRouter()


class TranslateResponse(BaseModel):
    original: str
    translation: str
    example_sentence: str | None
    card_id: str
    is_new_card: bool
    audio_base64: str        # base64 MP3 of the translation
    example_audio_base64: str | None  # base64 MP3 of the example sentence


@router.post("/translate")
async def instant_translate(
    text: str | None = Form(None),
    audio: UploadFile | None = File(None),
    card_type: str = Form("vocabulary"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TranslateResponse:
    """
    Translate a word or phrase into your target language, add it to your SRS deck,
    and return TTS audio of the translation + an example sentence.

    Input (one required):
    - text: form field with the phrase
    - audio: WebM recording, transcribed via STT first

    Response includes base64 MP3 audio for both the translation and the example sentence.
    """
    if not user.target_language:
        raise HTTPException(
            status_code=400, detail="Target language not set — update it in settings"
        )

    known = json.loads(user.known_languages) if user.known_languages else []
    native = known[0] if known else "en"
    target = user.target_language

    # 1. Resolve input phrase (text or STT)
    if audio is not None:
        audio_bytes = await audio.read()
        try:
            original = await app_llm.transcribe_audio(
                audio_bytes, audio.filename or "recording.webm", native
            )
            original = original.strip()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}") from exc
    elif text:
        original = text.strip()
    else:
        raise HTTPException(status_code=400, detail="Provide either 'text' or 'audio'")

    if not original:
        raise HTTPException(status_code=400, detail="Empty input after processing")

    # 2. Translate + generate example sentence in one LLM call
    prompt = (
        f'You are a language learning assistant. The user knows {native} and is learning {target}.\n'
        f'Translate the following phrase into {target} and produce one natural example sentence '
        f'in {target} that uses the translation in context.\n'
        f'Phrase: "{original}"\n\n'
        f'Reply ONLY with valid JSON in this exact shape:\n'
        f'{{"translation": "<the translation>", "example": "<example sentence in {target}>"}}'
    )
    try:
        raw = await app_llm.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=app_llm.summarization_model(),
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        data = json.loads(raw)
        translation = data.get("translation", "").strip().strip('"')
        example_sentence = data.get("example", "").strip() or None
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Translation failed: {exc}") from exc

    if not translation:
        raise HTTPException(status_code=502, detail="LLM returned empty translation")

    # 3. Check existence, then upsert SRS card with context sentence
    existing_result = await db.execute(
        select(SRSCard).where(
            SRSCard.user_id == user.id,
            SRSCard.front == translation,
            SRSCard.language == target,
        )
    )
    existing_card = existing_result.scalar_one_or_none()
    is_new_card = existing_card is None

    valid_card_type = card_type if card_type in ("vocabulary", "phrase", "grammar") else "vocabulary"
    card = await srs_service.find_or_create_card(
        db,
        user_id=user.id,
        word=translation,
        language=target,
        back=original,
        card_type=valid_card_type,
        context_sentence=example_sentence,
        source="instant_assistant",
    )

    # 4. TTS: speak translation and example sentence in parallel
    async def _speak(t: str) -> bytes:
        return await app_llm.speak(t)

    import asyncio
    tts_tasks = [_speak(translation)]
    if example_sentence:
        tts_tasks.append(_speak(example_sentence))

    try:
        tts_results = await asyncio.gather(*tts_tasks)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TTS failed: {exc}") from exc

    translation_audio_b64 = base64.b64encode(tts_results[0]).decode("utf-8")
    example_audio_b64 = base64.b64encode(tts_results[1]).decode("utf-8") if example_sentence else None

    return TranslateResponse(
        original=original,
        translation=translation,
        example_sentence=example_sentence,
        card_id=card.id,
        is_new_card=is_new_card,
        audio_base64=translation_audio_b64,
        example_audio_base64=example_audio_b64,
    )
