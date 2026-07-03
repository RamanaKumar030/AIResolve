import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.chat_service import ChatService
from app.schemas.chat import (
    SendMessageRequest,
    SendMessageResponse,
    ConversationResponse,
    ConversationDetailResponse,
    ConversationCreateRequest,
)
from app.api.deps import get_current_user
from app.db.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    body: ConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat_service = ChatService(db)
    conv = await chat_service.conversation_repo.create(
        user_id=current_user.id, title=body.title
    )
    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        is_archived=conv.is_archived,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=0,
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat_service = ChatService(db)
    convs = await chat_service.get_user_conversations(
        current_user.id, skip, limit
    )
    result = []
    for conv in convs:
        msg_count = await chat_service.message_repo.count(conversation_id=conv.id)
        result.append(
            ConversationResponse(
                id=conv.id,
                title=conv.title,
                is_archived=conv.is_archived,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=msg_count,
            )
        )
    return result


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat_service = ChatService(db)
    detail = await chat_service.get_conversation_detail(
        conversation_id, current_user.id
    )
    if not detail:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return detail


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat_service = ChatService(db)
    deleted = await chat_service.delete_conversation(
        conversation_id, current_user.id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.get("/search")
async def search_conversations(
    q: str = Query("", min_length=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat_service = ChatService(db)
    convs = await chat_service.search_conversations(current_user.id, q)
    result = []
    for conv in convs:
        msg_count = await chat_service.message_repo.count(conversation_id=conv.id)
        result.append(
            ConversationResponse(
                id=conv.id,
                title=conv.title,
                is_archived=conv.is_archived,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=msg_count,
            )
        )
    return result


@router.post("/send")
async def send_message(
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat_service = ChatService(db)

    conv = await chat_service.get_or_create_conversation(
        body.conversation_id, current_user.id, body.content
    )

    user_msg = await chat_service.save_user_message(conv.id, body.content)

    if conv.title == "New Conversation":
        conv = await chat_service.conversation_repo.update(
            conv.id, title=body.content[:80]
        )

    history = await chat_service.get_conversation_history(conv.id)

    async def generate():
        full_response = ""
        try:
            async for chunk in chat_service.stream_response(conv.id, history):
                full_response += chunk
                yield json.dumps({"type": "chunk", "content": chunk}) + "\n"

            assistant_msg = await chat_service.save_assistant_message(
                conv.id, full_response
            )
            await db.commit()

            yield json.dumps({
                "type": "done",
                "conversation_id": conv.id,
                "message_id": assistant_msg.id,
                "content": full_response,
            }) + "\n"

        except Exception as e:
            logger.error("Stream error: %s", str(e))
            yield json.dumps({"type": "error", "error": str(e)}) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "X-Conversation-Id": conv.id,
            "Cache-Control": "no-cache",
        },
    )
