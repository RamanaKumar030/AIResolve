from sqlalchemy import select, desc
from app.db.models.conversation import Conversation
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, session):
        super().__init__(Conversation, session)

    async def get_user_conversations(
        self, user_id: str, skip: int = 0, limit: int = 50
    ) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.is_archived == False)
            .order_by(desc(Conversation.updated_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_user_conversations(
        self, user_id: str, query: str, skip: int = 0, limit: int = 20
    ) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.is_archived == False,
                Conversation.title.ilike(f"%{query}%"),
            )
            .order_by(desc(Conversation.updated_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
