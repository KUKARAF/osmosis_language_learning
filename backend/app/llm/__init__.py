"""
osmosis LLM abstraction.

Use model strings in the format  "provider/model-name":
    "groq/llama-3.3-70b-versatile"
    "openrouter/anthropic/claude-sonnet-4-5"
    "openrouter/google/gemini-2.0-flash-001"

The provider prefix is stripped before calling the underlying API.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from app import config
from app.config import settings


def _provider(name: str):
    """Lazily import and return a provider instance by name."""
    if name == "groq":
        from app.llm.providers.groq import GroqProvider
        return GroqProvider()
    if name == "openrouter":
        from app.llm.providers.openrouter import OpenRouterProvider
        return OpenRouterProvider()
    raise ValueError(f"Unknown LLM provider {name!r}. Use 'groq' or 'openrouter'.")


def _parse(model_str: str) -> tuple[str, str]:
    """Split 'provider/model' into ('provider', 'model').

    Examples:
        'groq/llama-3.3-70b-versatile'        → ('groq', 'llama-3.3-70b-versatile')
        'openrouter/anthropic/claude-sonnet'   → ('openrouter', 'anthropic/claude-sonnet')
    """
    provider, sep, model = model_str.partition("/")
    if not sep:
        raise ValueError(
            f"Invalid model string {model_str!r}. Expected 'provider/model-name'."
        )
    return provider, model


def summarization_model() -> str:
    """Return the preferred model string for fast summarization / translation tasks."""
    if settings.GROQ_API_KEY:
        return "groq/llama-3.3-70b-versatile"
    return f"openrouter/{config.SUMMARIZATION_MODEL}"


async def chat_completion(
    messages: list[dict],
    model: str,
    *,
    temperature: float = 0.7,
    response_format: dict | None = None,
) -> str:
    """Non-streaming chat completion. Returns the response text."""
    provider_name, model_id = _parse(model)
    return await _provider(provider_name).chat_completion(
        messages=messages,
        model=model_id,
        temperature=temperature,
        response_format=response_format,
    )


async def chat_completion_stream(
    messages: list[dict],
    model: str,
    *,
    tools: list[dict] | None = None,
    temperature: float = 0.7,
) -> AsyncIterator[dict]:
    """Streaming chat completion. Yields raw chunk dicts."""
    provider_name, model_id = _parse(model)
    async for chunk in _provider(provider_name).chat_completion_stream(
        messages=messages,
        model=model_id,
        tools=tools,
        temperature=temperature,
    ):
        yield chunk
