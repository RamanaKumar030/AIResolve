import logging
from typing import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.message_repo import MessageRepository
from app.repositories.vote_repo import VoteRepository
from app.repositories.feedback_repo import FeedbackRepository
from app.db.models.message import Message, MessageRole
from app.db.models.conversation import Conversation
from app.services.openai_service import stream_chat_response

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.conversation_repo = ConversationRepository(session)
        self.message_repo = MessageRepository(session)
        self.vote_repo = VoteRepository(session)
        self.feedback_repo = FeedbackRepository(session)

    async def get_or_create_conversation(
        self, conversation_id: str | None, user_id: str, content: str
    ) -> Conversation:
        if conversation_id:
            conv = await self.conversation_repo.get(conversation_id)
            if conv and conv.user_id == user_id:
                return conv
        title = content[:80] + "..." if len(content) > 80 else content
        return await self.conversation_repo.create(
            user_id=user_id, title=title
        )

    async def save_user_message(self, conversation_id: str, content: str) -> Message:
        return await self.message_repo.create(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=content,
        )

    async def save_assistant_message(
        self, conversation_id: str, content: str
    ) -> Message:
        return await self.message_repo.create(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=content,
        )

    async def get_conversation_history(
        self, conversation_id: str
    ) -> list[dict]:
        messages = await self.message_repo.get_conversation_messages(
            conversation_id
        )
        return [
            {"role": msg.role.value, "content": msg.content} for msg in messages
        ]

    async def stream_response(
        self, conversation_id: str, messages: list[dict]
    ) -> AsyncIterator[str]:
        async for chunk in stream_chat_response(messages, self.session):
            yield chunk

    async def get_user_conversations(
        self, user_id: str, skip: int = 0, limit: int = 50
    ) -> list[Conversation]:
        return await self.conversation_repo.get_user_conversations(
            user_id, skip, limit
        )

    async def get_conversation_detail(
        self, conversation_id: str, user_id: str
    ) -> Conversation | None:
        conv = await self.conversation_repo.get(conversation_id)
        if not conv or conv.user_id != user_id:
            return None
        messages = await self.message_repo.get_conversation_messages(conversation_id)
        result_messages = []
        for msg in messages:
            vote = await self.vote_repo.get_user_vote(msg.id, user_id)
            feedback = await self.feedback_repo.get_user_feedback(msg.id, user_id)
            result_messages.append({
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "role": msg.role.value,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "vote": vote.vote_type.value if vote else None,
                "feedback": feedback.reason if feedback else None,
            })
        return {
            "id": conv.id,
            "title": conv.title,
            "is_archived": conv.is_archived,
            "created_at": conv.created_at.isoformat(),
            "updated_at": conv.updated_at.isoformat(),
            "messages": result_messages,
        }

    async def search_conversations(
        self, user_id: str, query: str
    ) -> list[Conversation]:
        return await self.conversation_repo.search_user_conversations(
            user_id, query
        )

    async def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        conv = await self.conversation_repo.get(conversation_id)
        if not conv or conv.user_id != user_id:
            return False
        return await self.conversation_repo.delete(conversation_id)

    async def update_conversation_title(
        self, conversation_id: str, user_id: str, title: str
    ) -> Conversation | None:
        conv = await self.conversation_repo.get(conversation_id)
        if not conv or conv.user_id != user_id:
            return None
        return await self.conversation_repo.update(conversation_id, title=title)
