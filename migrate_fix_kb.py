"""
Data migration: Fix existing approved tickets that are missing KB entries or have wrong question.

This script:
1. Finds all APPROVED tickets
2. For each, ensures a KB entry exists with the correct student question
3. Fixes wrong questions (were set to AI answer text instead of student question)
4. Deactivates duplicate/superseded entries for the same question
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from app.db.session import async_session_factory
from app.db.models.knowledge_base import KnowledgeBase
from app.db.models.ticket import Ticket, TicketStatus
from app.db.models.feedback import Feedback
from app.db.models.message import Message, MessageRole
from app.services.openai_service import generate_embeddings


async def fix_existing():
    async with async_session_factory() as session:
        print("=" * 80)
        print("MIGRATION: Fix existing approved tickets")
        print("=" * 80)

        # Find all approved tickets (eagerly load feedback and message to avoid lazy loading issues)
        stmt = (
            select(Ticket)
            .options(
                selectinload(Ticket.feedback).selectinload(Feedback.message)
            )
            .where(Ticket.status == TicketStatus.APPROVED)
        )
        result = await session.execute(stmt)
        tickets = result.scalars().unique().all()
        print(f"\nFound {len(tickets)} approved tickets")

        fixed = 0
        for ticket in tickets:
            ticket_id = ticket.id
            answer = ticket.suggested_answer

            # Extract the actual student question
            question = "No question available"
            if ticket.feedback and ticket.feedback.message:
                msg = ticket.feedback.message
                conv_stmt = (
                    select(Message)
                    .where(
                        Message.conversation_id == msg.conversation_id,
                        Message.role == MessageRole.USER,
                        Message.created_at < msg.created_at,
                    )
                    .order_by(Message.created_at.desc())
                    .limit(1)
                )
                conv_result = await session.execute(conv_stmt)
                user_msg = conv_result.scalar_one_or_none()
                if user_msg:
                    question = user_msg.content

            wrong_question = ticket.feedback.message.content if ticket.feedback and ticket.feedback.message else ""
            needs_fix = False

            # Check if KB entry exists for this ticket
            kb_stmt = select(KnowledgeBase).where(
                KnowledgeBase.source_ticket_id == ticket_id
            )
            kb_result = await session.execute(kb_stmt)
            entry = kb_result.scalar_one_or_none()

            if entry:
                # Entry exists — check if question is wrong
                if entry.question != question:
                    print(f"\n  Ticket {ticket_id[:20]}...: FIXING wrong question")
                    print(f"    OLD question[:100]: {entry.question[:100]}")
                    print(f"    CORRECT question:   {question[:100]}")
                    entry.question = question
                    entry.answer = answer
                    # Re-embed with correct question
                    try:
                        embedding = await generate_embeddings(f"{question}\n{answer}")
                        entry.embedding = "[" + ",".join(str(v) for v in embedding) + "]"
                    except Exception as e:
                        print(f"    Warning: embedding failed: {e}")
                    needs_fix = True
            else:
                # No KB entry — create one
                print(f"\n  Ticket {ticket_id[:20]}...: CREATING missing KB entry")
                print(f"    question: {question[:100]}")
                try:
                    embedding = await generate_embeddings(f"{question}\n{answer}")
                    embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
                except Exception as e:
                    print(f"    Warning: embedding failed: {e}")
                    embedding_str = None

                entry = KnowledgeBase(
                    question=question,
                    answer=answer,
                    embedding=embedding_str,
                    source_ticket_id=ticket_id,
                    is_active=True,
                )
                session.add(entry)
                await session.flush()  # Ensure entry.id is assigned before stale check
                needs_fix = True

            if needs_fix:
                fixed += 1

            # Deactivate stale entries with same question (but different source_ticket_id)
            if question != "No question available":
                stale_stmt = select(KnowledgeBase).where(
                    KnowledgeBase.is_active == True,
                    KnowledgeBase.id != entry.id,
                    KnowledgeBase.question == question,
                )
                stale_result = await session.execute(stale_stmt)
                for stale in stale_result.scalars().all():
                    print(f"    Deactivating stale KB entry {stale.id[:20]}... (superseded)")
                    stale.is_active = False

        if fixed:
            await session.flush()
            await session.commit()
            print(f"\nOK - Fixed {fixed} ticket(s)")
        else:
            print(f"\nNo fixes needed — all approved tickets have correct KB entries")

        # Print summary
        print("\n" + "=" * 80)
        print("FINAL KB STATE")
        print("=" * 80)
        final = await session.execute(
            select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())
        )
        for e in final.scalars().all():
            print(f"\n  [{e.id[:20]}...] is_active={e.is_active}")
            print(f"    Q: {e.question[:100]}")
            print(f"    A: {e.answer[:100]}")
            print(f"    src_ticket: {e.source_ticket_id[:20]}...")

        print("\n" + "=" * 80)
        print("MIGRATION COMPLETE")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(fix_existing())
