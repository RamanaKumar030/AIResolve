import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        user_id: str,
        action: str,
        resource: str,
        resource_id: str,
        details: dict | None = None,
    ) -> AuditLog:
        audit = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details,
        )
        self.session.add(audit)
        await self.session.flush()
        logger.info("Audit: user=%s action=%s resource=%s/%s", user_id, action, resource, resource_id)
        return audit

    async def get_recent(
        self, limit: int = 20
    ) -> list[AuditLog]:
        from sqlalchemy import select, desc
        stmt = (
            select(AuditLog)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
