from sqlalchemy import select, desc
from app.db.models.ticket import Ticket, TicketStatus
from app.repositories.base import BaseRepository


class TicketRepository(BaseRepository[Ticket]):
    def __init__(self, session):
        super().__init__(Ticket, session)

    async def get_by_status(
        self, status: TicketStatus, skip: int = 0, limit: int = 50
    ) -> list[Ticket]:
        stmt = (
            select(Ticket)
            .where(Ticket.status == status)
            .order_by(desc(Ticket.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all(self, skip: int = 0, limit: int = 50) -> list[Ticket]:
        stmt = (
            select(Ticket)
            .order_by(desc(Ticket.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_stats(self) -> dict:
        total = await self.count()
        open_count = await self.count(status=TicketStatus.OPEN)
        in_review = await self.count(status=TicketStatus.IN_REVIEW)
        approved_count = await self.count(status=TicketStatus.APPROVED)
        rejected_count = await self.count(status=TicketStatus.REJECTED)
        return {
            "total": total,
            "open": open_count,
            "in_review": in_review,
            "approved": approved_count,
            "rejected": rejected_count,
        }
