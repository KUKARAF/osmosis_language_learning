import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation, Message
from app import llm as app_llm
from app.llm.prompt_loader import registry as prompt_registry

log = logging.getLogger(__name__)

RECENT_TURNS_TO_KEEP = 3
TOOL_CONTENT_MAX_LEN = 200


def _msg_to_dict(msg: Message) -> dict:
    """Convert a Message ORM object to an LLM message dict."""
    entry: dict = {"role": msg.role}
    if msg.content:
        entry["content"] = msg.content
    if msg.tool_calls:
        entry["tool_calls"] = json.loads(msg.tool_calls)
    if msg.tool_call_id:
        entry["tool_call_id"] = msg.tool_call_id
    return entry


def _truncate_tool_content(content: str) -> str:
    """Truncate tool result content for summarization input."""
    if len(content) <= TOOL_CONTENT_MAX_LEN:
        return content
    return content[:TOOL_CONTENT_MAX_LEN] + "…[truncated]"


def _msgs_to_text(messages: list[Message]) -> str:
    """Format messages as readable text for the summarization prompt."""
    lines = []
    for msg in messages:
        role = msg.role.upper()
        if msg.role == "tool":
            content = _truncate_tool_content(msg.content or "")
            lines.append(f"[TOOL RESULT]: {content}")
        elif msg.role == "assistant" and msg.tool_calls:
            calls = json.loads(msg.tool_calls)
            names = ", ".join(c["function"]["name"] for c in calls)
            text = msg.content or ""
            lines.append(f"{role}: {text} [called tools: {names}]")
        else:
            lines.append(f"{role}: {msg.content or ''}")
    return "\n".join(lines)


def _find_user_turn_indices(messages: list[Message]) -> list[int]:
    """Return indices of messages with role='user' (turn boundaries)."""
    return [i for i, m in enumerate(messages) if m.role == "user"]


async def _generate_summary(
    existing_summary: str | None,
    messages: list[Message],
) -> str:
    """Call the summarization LLM to produce a (possibly incremental) summary."""
    conversation_text = _msgs_to_text(messages)

    if existing_summary:
        prompt_name = "summarization_incremental"
        user_content = (
            f"## Existing Summary\n{existing_summary}\n\n"
            f"## New Messages\n{conversation_text}"
        )
    else:
        prompt_name = "summarization"
        user_content = conversation_text

    meta, system_prompt = prompt_registry.render(prompt_name)
    model = meta.get("model", app_llm.summarization_model())
    llm_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    summary = await app_llm.chat_completion(llm_messages, model=model)
    return summary.strip()


async def build_context_with_summary(
    db: AsyncSession, conversation: Conversation
) -> list[dict]:
    """Build the message list for the LLM, summarizing old turns if needed.

    Returns a list of message dicts ready to append after the system prompt.
    """
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    all_messages: list[Message] = list(result.scalars().all())

    if not all_messages:
        return []

    user_indices = _find_user_turn_indices(all_messages)

    # If 3 or fewer user turns, return everything as-is
    if len(user_indices) <= RECENT_TURNS_TO_KEEP:
        return [_msg_to_dict(m) for m in all_messages]

    # Split at the 3rd-from-last user message
    split_idx = user_indices[-RECENT_TURNS_TO_KEEP]
    older_messages = all_messages[:split_idx]
    recent_messages = all_messages[split_idx:]

    if not older_messages:
        return [_msg_to_dict(m) for m in all_messages]

    last_older_msg_id = older_messages[-1].id

    # Check if summary is stale
    if conversation.summary_through_msg_id != last_older_msg_id:
        # Find messages not yet covered by existing summary
        if conversation.summary_through_msg_id and conversation.summary:
            # Incremental: find where old summary ended
            covered_idx = None
            for i, m in enumerate(older_messages):
                if m.id == conversation.summary_through_msg_id:
                    covered_idx = i
                    break
            if covered_idx is not None:
                new_messages = older_messages[covered_idx + 1:]
            else:
                # Can't find the marker — resummarize everything
                new_messages = older_messages
                conversation.summary = None
        else:
            new_messages = older_messages

        if new_messages:
            log.info(
                "Summarizing %d messages for conversation %s (incremental=%s)",
                len(new_messages),
                conversation.id,
                conversation.summary is not None,
            )
            conversation.summary = await _generate_summary(
                conversation.summary, new_messages
            )
        conversation.summary_through_msg_id = last_older_msg_id
        await db.commit()

    # Build final context
    context: list[dict] = []
    if conversation.summary:
        context.append({
            "role": "system",
            "content": f"[Previous conversation summary]\n{conversation.summary}",
        })
    context.extend(_msg_to_dict(m) for m in recent_messages)
    return context
