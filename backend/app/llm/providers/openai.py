"""OpenAI provider — api.openai.com."""
from __future__ import annotations

import httpx

from app.config import settings

_BASE_URL = "https://api.openai.com/v1"


class OpenAIProvider:
    def _auth_header(self) -> dict:
        return {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}

    async def speak(
        self,
        text: str,
        voice: str = "alloy",
        model: str = "tts-1",
    ) -> bytes:
        """Synthesize speech via OpenAI TTS. Returns mp3 bytes."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{_BASE_URL}/audio/speech",
                headers={**self._auth_header(), "Content-Type": "application/json"},
                json={"model": model, "input": text, "voice": voice},
            )
            resp.raise_for_status()
            return resp.content
