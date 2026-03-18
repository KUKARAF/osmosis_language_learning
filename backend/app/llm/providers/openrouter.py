"""OpenRouter provider — OpenAI-compatible API at openrouter.ai."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.config import settings

_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider:
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://app.osmosis.page",
            "X-Title": "osmosis",
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
        voice: str = "alloy",
        model: str = "openai/tts-1",
    ) -> bytes:
        """Synthesize speech via OpenRouter /audio/speech. Returns mp3 bytes."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{_BASE_URL}/audio/speech",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "HTTP-Referer": "https://app.osmosis.page",
                    "X-Title": "osmosis",
                },
                json={"model": model, "input": text, "voice": voice},
            )
            resp.raise_for_status()
            return resp.content

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
