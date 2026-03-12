from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Conversation, Message
from app.schemas import MessageCreate, MessageResponse, ConversationResponse
from app.services import chat_service, cat_service

router = APIRouter()


@router.get("/conversations")
async def list_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationResponse]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
    )
    return [
        ConversationResponse(
            id=c.id, cat_id=c.cat_id, title=c.title, created_at=c.created_at
        )
        for c in result.scalars().all()
    ]


@router.post("/conversations")
async def create_conversation(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    cat = await cat_service.get_active_cat(db, user)
    if cat is None:
        # User has no target language yet — create a temporary conversation
        from app.models import Cat, _uuid, _utcnow
        cat = Cat(
            id=_uuid(), user_id=user.id, language="unknown",
            state="happy", created_at=_utcnow(),
        )
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

    conv = await chat_service.get_or_create_conversation(db, user, cat)
    return ConversationResponse(
        id=conv.id, cat_id=conv.cat_id, title=conv.title, created_at=conv.created_at
    )


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageResponse]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            tool_calls=m.tool_calls,
            tool_call_id=m.tool_call_id,
            token_count=m.token_count,
            created_at=m.created_at,
        )
        for m in result.scalars().all()
    ]


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    body: MessageCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return StreamingResponse(
        chat_service.handle_message(db, user, conversation_id, body.content),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
