from sqlalchemy import select, desc
from app.db.models.message import Message, MessageRole
from app.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    def __init__(self, session):
        super().__init__(Message, session)

    async def get_conversation_messages(
        self, conversation_id: str, limit: int = 100
    ) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_assistant_messages(
        self, user_id: str, limit: int = 10
    ) -> list[Message]:
        stmt = (
            select(Message)
            .join(Message.conversation)
            .where(
                Message.role == MessageRole.ASSISTANT,
                Message.conversation.has(user_id=user_id),
            )
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_messages(
        self, conversation_id: str, query: str, limit: int = 50
    ) -> list[Message]:
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.content.ilike(f"%{query}%"),
            )
            .order_by(Message.created_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
