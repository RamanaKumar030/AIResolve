from sqlalchemy import select
from app.db.models.vote import Vote, VoteType
from app.repositories.base import BaseRepository


class VoteRepository(BaseRepository[Vote]):
    def __init__(self, session):
        super().__init__(Vote, session)

    async def get_user_vote(self, message_id: str, user_id: str) -> Vote | None:
        stmt = select(Vote).where(
            Vote.message_id == message_id, Vote.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_message_vote_counts(self, message_id: str) -> dict[str, int]:
        upvotes = await self.count(message_id=message_id, vote_type=VoteType.UPVOTE)
        downvotes = await self.count(message_id=message_id, vote_type=VoteType.DOWNVOTE)
        return {"upvotes": upvotes, "downvotes": downvotes}

    async def upsert_vote(
        self, message_id: str, user_id: str, vote_type: VoteType
    ) -> Vote | None:
        existing = await self.get_user_vote(message_id, user_id)
        if existing:
            if existing.vote_type == vote_type:
                await self.delete(existing.id)
                return None
            existing.vote_type = vote_type
            await self.session.flush()
            return existing
        return await self.create(
            message_id=message_id, user_id=user_id, vote_type=vote_type
        )
