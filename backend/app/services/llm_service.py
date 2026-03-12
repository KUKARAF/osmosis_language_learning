import json
from collections.abc import AsyncIterator

import httpx

from app.config import settings

PROVIDERS = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "api_key_attr": "OPENROUTER_API_KEY",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "api_key_attr": "GROQ_API_KEY",
    },
}


async def chat_completion_stream(
    messages: list[dict],
    tools: list[dict] | None = None,
    provider: str = "openrouter",
) -> AsyncIterator[dict]:
    """Stream chat completions from OpenRouter or Groq (OpenAI-compatible API)."""
    prov = PROVIDERS[provider]
    api_key = getattr(settings, prov["api_key_attr"])

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://app.osmosis.page"
        headers["X-Title"] = "osmosis"

    body: dict = {
        "model": prov["model"],
        "messages": messages,
        "stream": True,
    }
    if tools:
        body["tools"] = tools

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            f"{prov['base_url']}/chat/completions",
            headers=headers,
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
                    chunk = json.loads(data)
                    yield chunk
                except json.JSONDecodeError:
                    continue


def select_provider(context: str = "") -> str:
    """Pick provider based on context. Default to openrouter."""
    if settings.GROQ_API_KEY and "quick" in context.lower():
        return "groq"
    return "openrouter"


def count_tokens(messages: list[dict]) -> int:
    """Rough token estimate (chars / 4)."""
    total = 0
    for msg in messages:
        content = msg.get("content") or ""
        total += len(content)
    return total // 4
