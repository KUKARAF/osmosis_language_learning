"""LemonFox provider — api.lemonfox.ai (OpenAI-compatible TTS)."""
from __future__ import annotations

import httpx

from app.config import settings

_BASE_URL = "https://api.lemonfox.ai/v1"


class LemonFoxProvider:
    def _auth_header(self) -> dict:
        return {"Authorization": f"Bearer {settings.LEMONFOX_API_KEY}"}

    async def speak(
        self,
        text: str,
        voice: str = "sarah",
    ) -> bytes:
        """Synthesize speech via LemonFox TTS. Returns mp3 bytes."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{_BASE_URL}/audio/speech",
                headers={**self._auth_header(), "Content-Type": "application/json"},
                json={"input": text, "voice": voice, "response_format": "mp3"},
            )
            resp.raise_for_status()
            return resp.content
