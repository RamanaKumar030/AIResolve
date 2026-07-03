from sqlalchemy import select
from app.db.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_supabase_uid(self, supabase_uid: str) -> User | None:
        stmt = select(User).where(User.supabase_uid == supabase_uid)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
