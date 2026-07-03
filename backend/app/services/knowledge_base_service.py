import logging
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.knowledge_base_repo import KnowledgeBaseRepository
from app.repositories.ticket_repo import TicketRepository
from app.db.models.ticket import Ticket, TicketStatus
from app.db.models.feedback import Feedback
from app.db.models.knowledge_base import KnowledgeBase
from app.db.models.message import Message, MessageRole
from app.services.openai_service import generate_embeddings

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.kb_repo = KnowledgeBaseRepository(session)
        self.ticket_repo = TicketRepository(session)

    async def add_from_ticket(self, ticket_id: str) -> KnowledgeBase | None:
        # Eagerly load feedback and message to avoid async lazy-loading issues
        stmt = (
            select(Ticket)
            .options(
                selectinload(Ticket.feedback).selectinload(Feedback.message)
            )
            .where(Ticket.id == ticket_id)
        )
        result = await self.session.execute(stmt)
        ticket = result.scalars().unique().one_or_none()
        if not ticket:
            logger.warning("Ticket %s not found", ticket_id)
            return None

        answer = ticket.suggested_answer

        # Extract the actual student question from the conversation, not from
        # ticket.feedback.message.content (which is the AI's answer, not the question)
        question = "No question available"
        if ticket.feedback and ticket.feedback.message:
            msg = ticket.feedback.message
            stmt = (
                select(Message)
                .where(
                    Message.conversation_id == msg.conversation_id,
                    Message.role == MessageRole.USER,
                    Message.created_at < msg.created_at,
                )
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            result = await self.session.execute(stmt)
            user_msg = result.scalar_one_or_none()
            if user_msg:
                question = user_msg.content

        # Check if a KB entry already exists for this ticket (update-in-place)
        existing_stmt = select(KnowledgeBase).where(
            KnowledgeBase.source_ticket_id == ticket_id
        )
        existing_result = await self.session.execute(existing_stmt)
        existing_entry = existing_result.scalar_one_or_none()

        try:
            embedding = await generate_embeddings(f"{question}\n{answer}")
            embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
        except Exception as e:
            logger.warning("Failed to generate embedding: %s", e)
            embedding_str = None

        if existing_entry:
            # Update in place — preserves the same row so retrieval is consistent
            existing_entry.question = question
            existing_entry.answer = answer
            existing_entry.embedding = embedding_str
            await self.session.flush()
            entry = existing_entry
            logger.info(
                "Updated knowledge base entry %s from ticket %s",
                entry.id, ticket_id,
            )
        else:
            entry = await self.kb_repo.create(
                question=question,
                answer=answer,
                embedding=embedding_str,
                source_ticket_id=ticket_id,
            )
            logger.info(
                "Added knowledge base entry %s from ticket %s",
                entry.id, ticket_id,
            )

        # Deactivate any OTHER active entries with the same question text,
        # so the retrieval path can only ever see the latest approved answer
        # for this question.
        deactivate_stmt = (
            select(KnowledgeBase)
            .where(
                KnowledgeBase.is_active == True,
                KnowledgeBase.id != entry.id,
                KnowledgeBase.question == question,
            )
        )
        deactivate_result = await self.session.execute(deactivate_stmt)
        stale_entries = deactivate_result.scalars().all()
        for stale in stale_entries:
            stale.is_active = False
            logger.info(
                "Deactivated stale KB entry %s (superseded by %s)",
                stale.id, entry.id,
            )
        if stale_entries:
            await self.session.flush()

        return entry

    async def search_similar(
        self, query: str, limit: int = 5
    ) -> list[tuple[KnowledgeBase, float]]:
        try:
            embedding = await generate_embeddings(query)
            return await self.kb_repo.search_similar(embedding, limit=limit)
        except Exception as e:
            logger.warning("Similarity search failed: %s", e)
            return []

    async def get_all_entries(
        self, skip: int = 0, limit: int = 50
    ) -> list[KnowledgeBase]:
        return await self.kb_repo.get_active_entries(skip, limit)

    async def update_entry(
        self, entry_id: str, **kwargs
    ) -> KnowledgeBase | None:
        return await self.kb_repo.update(entry_id, **kwargs)

    async def delete_entry(self, entry_id: str) -> bool:
        return await self.kb_repo.delete(entry_id)
