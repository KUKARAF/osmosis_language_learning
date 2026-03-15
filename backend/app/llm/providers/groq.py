"""Groq provider — OpenAI-compatible API at api.groq.com."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.config import settings

_BASE_URL = "https://api.groq.com/openai/v1"


class GroqProvider:
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

    async def chat_completion(
        self,
        messages: list[dict],
        model: str,
        *,
        temperature: float = 0.7,
        response_format: dict | None = None,
    ) -> str:
        body: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if response_format:
            body["response_format"] = response_format

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{_BASE_URL}/chat/completions",
                headers=self._headers(),
                json=body,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def speak(
        self,
        text: str,
        voice: str = "Aria-PlayAI",
    ) -> bytes:
        """Synthesize speech using Groq PlayAI TTS. Returns raw mp3 bytes."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{_BASE_URL}/audio/speech",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                json={"model": "playai-tts", "input": text, "voice": voice},
            )
            resp.raise_for_status()
            return resp.content

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        language: str,
    ) -> str:
        """Transcribe audio using Groq Whisper."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{_BASE_URL}/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                files={"file": (filename, audio_bytes, "audio/webm")},
                data={"model": "whisper-large-v3-turbo", "language": language},
            )
            resp.raise_for_status()
            return resp.json()["text"]

    async def chat_completion_stream(
        self,
        messages: list[dict],
        model: str,
        *,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[dict]:
        body: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if tools:
            body["tools"] = tools

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{_BASE_URL}/chat/completions",
                headers=self._headers(),
                json=body,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        yield {"type": "done"}
                        return
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue
