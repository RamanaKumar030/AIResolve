import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import create_access_token
from app.repositories.user_repo import UserRepository
from app.db.models.user import User, UserRole

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession):
        self.user_repo = UserRepository(session)

    async def authenticate_or_create(self, supabase_uid: str, email: str, full_name: str) -> tuple[User, str]:
        user = await self.user_repo.get_by_supabase_uid(supabase_uid)
        if not user:
            user = await self.user_repo.get_by_email(email)
            if user:
                user = await self.user_repo.update(user.id, supabase_uid=supabase_uid, full_name=full_name)
            else:
                user = await self.user_repo.create(
                    email=email,
                    full_name=full_name,
                    supabase_uid=supabase_uid,
                    role=UserRole.STUDENT,
                )
            logger.info("Created user %s with email %s", user.id, email)
        token = create_access_token(subject=user.id, extra_claims={"role": user.role.value, "email": user.email})
        return user, token

    async def get_user(self, user_id: str) -> User | None:
        return await self.user_repo.get(user_id)

    async def update_user(self, user_id: str, **kwargs) -> User | None:
        return await self.user_repo.update(user_id, **kwargs)
