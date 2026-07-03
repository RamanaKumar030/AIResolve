import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.vote_repo import VoteRepository
from app.repositories.feedback_repo import FeedbackRepository
from app.repositories.message_repo import MessageRepository
from app.db.models.vote import Vote, VoteType
from app.db.models.feedback import Feedback
from app.db.models.message import MessageRole
from app.services.openai_service import generate_feedback_analysis

logger = logging.getLogger(__name__)


class FeedbackService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.vote_repo = VoteRepository(session)
        self.feedback_repo = FeedbackRepository(session)
        self.message_repo = MessageRepository(session)

    async def toggle_vote(
        self, message_id: str, user_id: str, vote_type: str
    ) -> dict | None:
        vt = VoteType.UPVOTE if vote_type == "upvote" else VoteType.DOWNVOTE
        result = await self.vote_repo.upsert_vote(message_id, user_id, vt)
        if result is None:
            return {"message_id": message_id, "vote_type": None}
        return {"message_id": message_id, "vote_type": result.vote_type.value}

    async def submit_feedback(
        self, message_id: str, user_id: str, reason: str
    ) -> Feedback:
        return await self.feedback_repo.create(
            message_id=message_id,
            user_id=user_id,
            reason=reason,
        )

    async def get_user_feedback(
        self, message_id: str, user_id: str
    ) -> Feedback | None:
        return await self.feedback_repo.get_user_feedback(message_id, user_id)

    async def get_user_vote(self, message_id: str, user_id: str) -> Vote | None:
        return await self.vote_repo.get_user_vote(message_id, user_id)
