import json
from collections.abc import AsyncIterator
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Cat, Conversation, Message, _uuid, _utcnow
from app.services import llm_service, cat_service
from app.tools.definitions import TOOLS
from app.tools.executor import ToolExecutor

_templates_dir = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_templates_dir)))

MAX_TOOL_ITERATIONS = 5


async def get_or_create_conversation(
    db: AsyncSession, user: User, cat: Cat
) -> Conversation:
    """Get the most recent conversation or create a new one."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id, Conversation.cat_id == cat.id)
        .order_by(Conversation.created_at.desc())
        .limit(1)
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        conv = Conversation(
            id=_uuid(),
            user_id=user.id,
            cat_id=cat.id,
            created_at=_utcnow(),
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
    return conv


async def build_system_prompt(user: User, cat: Cat) -> str:
    """Render the system prompt from a Jinja template."""
    known = json.loads(user.known_languages) if user.known_languages else []

    if not user.target_language:
        template = _jinja_env.get_template("onboarding.jinja")
    else:
        template = _jinja_env.get_template("system.jinja")

    return template.render(
        user=user,
        cat=cat,
        known_languages=known,
    )


async def handle_message(
    db: AsyncSession, user: User, conversation_id: str, user_message: str
) -> AsyncIterator[str]:
    """Full chat turn: persist → LLM → tools → stream SSE."""
    # Load conversation
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        yield _sse("error", {"message": "Conversation not found"})
        return

    cat = await cat_service.get_active_cat(db, user)

    # Persist user message
    user_msg = Message(
        id=_uuid(),
        conversation_id=conversation_id,
        role="user",
        content=user_message,
        created_at=_utcnow(),
    )
    db.add(user_msg)
    await db.commit()

    # Build messages array
    history = await _load_history(db, conversation_id)
    system_prompt = await build_system_prompt(user, cat)
    messages = [{"role": "system", "content": system_prompt}] + history

    executor = ToolExecutor(db)
    assistant_content = ""
    total_tokens = 0
    iteration = 0

    while iteration < MAX_TOOL_ITERATIONS:
        iteration += 1
        accumulated_tool_calls = []
        current_content = ""

        async for chunk in llm_service.chat_completion_stream(
            messages, tools=TOOLS
        ):
            if chunk.get("type") == "done":
                break

            choices = chunk.get("choices", [])
            if not choices:
                continue
            delta = choices[0].get("delta", {})

            # Stream text content
            if delta.get("content"):
                text = delta["content"]
                current_content += text
                yield _sse("token", {"content": text})

            # Accumulate tool calls
            if delta.get("tool_calls"):
                for tc_delta in delta["tool_calls"]:
                    idx = tc_delta.get("index", 0)
                    while len(accumulated_tool_calls) <= idx:
                        accumulated_tool_calls.append(
                            {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
                        )
                    tc = accumulated_tool_calls[idx]
                    if tc_delta.get("id"):
                        tc["id"] = tc_delta["id"]
                    fn = tc_delta.get("function", {})
                    if fn.get("name"):
                        tc["function"]["name"] += fn["name"]
                    if fn.get("arguments"):
                        tc["function"]["arguments"] += fn["arguments"]

            # Usage stats
            usage = chunk.get("usage")
            if usage:
                total_tokens += usage.get("total_tokens", 0)

        assistant_content += current_content

        if not accumulated_tool_calls:
            break

        # Process tool calls
        # Persist assistant message with tool_calls
        asst_msg = Message(
            id=_uuid(),
            conversation_id=conversation_id,
            role="assistant",
            content=current_content or None,
            tool_calls=json.dumps(accumulated_tool_calls),
            created_at=_utcnow(),
        )
        db.add(asst_msg)
        await db.commit()

        for tc in accumulated_tool_calls:
            yield _sse("tool_call", {
                "name": tc["function"]["name"],
                "arguments": json.loads(tc["function"]["arguments"]),
            })

        # Execute tools
        tool_results = await executor.execute(accumulated_tool_calls, user)
        for tr in tool_results:
            yield _sse("tool_result", {
                "tool_call_id": tr["tool_call_id"],
                "result": json.loads(tr["content"]),
            })
            # Persist tool result message
            tool_msg = Message(
                id=_uuid(),
                conversation_id=conversation_id,
                role="tool",
                content=tr["content"],
                tool_call_id=tr["tool_call_id"],
                created_at=_utcnow(),
            )
            db.add(tool_msg)

        await db.commit()

        # Rebuild messages for next iteration
        messages.append({
            "role": "assistant",
            "content": current_content or None,
            "tool_calls": accumulated_tool_calls,
        })
        for tr in tool_results:
            messages.append({
                "role": "tool",
                "tool_call_id": tr["tool_call_id"],
                "content": tr["content"],
            })

        assistant_content = ""

    # Persist final assistant message (if there was content without tool calls)
    if assistant_content:
        final_msg = Message(
            id=_uuid(),
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
            token_count=total_tokens,
            created_at=_utcnow(),
        )
        db.add(final_msg)
        user.tokens_used_today += total_tokens
        user.updated_at = _utcnow()
        await db.commit()

    yield _sse("done", {"tokens_used": total_tokens})


async def _load_history(db: AsyncSession, conversation_id: str) -> list[dict]:
    """Load conversation messages as dicts for the LLM."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = []
    for msg in result.scalars().all():
        entry: dict = {"role": msg.role}
        if msg.content:
            entry["content"] = msg.content
        if msg.tool_calls:
            entry["tool_calls"] = json.loads(msg.tool_calls)
        if msg.tool_call_id:
            entry["tool_call_id"] = msg.tool_call_id
        messages.append(entry)
    return messages


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
