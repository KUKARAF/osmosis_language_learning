"""
Compatibility shim — delegates to app.llm.

New code should import from `app.llm` directly using model strings like
"groq/llama-3.3-70b-versatile" or "openrouter/anthropic/claude-sonnet-4-5".
"""
from __future__ import annotations

from app import llm as _llm


async def chat_completion_stream(messages, tools=None, provider="openrouter"):
    model = (
        "openrouter/anthropic/claude-sonnet-4-5"
        if provider == "openrouter"
        else "groq/llama-3.3-70b-versatile"
    )
    async for chunk in _llm.chat_completion_stream(messages, model=model, tools=tools):
        yield chunk


async def chat_completion(messages, provider="openrouter", model=None):
    if model is None:
        model_str = _llm.summarization_model()
    elif "/" in model:
        model_str = model  # already qualified
    else:
        model_str = f"{provider}/{model}"
    return await _llm.chat_completion(messages, model=model_str)


def get_summarization_provider() -> tuple[str, str]:
    model_str = _llm.summarization_model()
    provider, model = model_str.split("/", 1)
    return provider, model


def count_tokens(messages: list[dict]) -> int:
    total = sum(len(msg.get("content") or "") for msg in messages)
    return total // 4
