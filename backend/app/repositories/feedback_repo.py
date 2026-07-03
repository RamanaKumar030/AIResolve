from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from app.db.models.feedback import Feedback
from app.db.models.ticket import Ticket
from app.repositories.base import BaseRepository


class FeedbackRepository(BaseRepository[Feedback]):
    def __init__(self, session):
        super().__init__(Feedback, session)

    async def get_user_feedback(self, message_id: str, user_id: str) -> Feedback | None:
        stmt = select(Feedback).where(
            Feedback.message_id == message_id, Feedback.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_with_tickets(
        self, skip: int = 0, limit: int = 50
    ) -> list[Feedback]:
        stmt = (
            select(Feedback)
            .options(selectinload(Feedback.ticket), selectinload(Feedback.user))
            .order_by(desc(Feedback.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
