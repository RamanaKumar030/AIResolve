"""Diagnostic script to query current knowledge_base state and find the bug."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import select, text as sqltext
from app.db.session import async_session_factory
from app.db.models.knowledge_base import KnowledgeBase
from app.db.models.ticket import Ticket, TicketStatus
from app.db.models.feedback import Feedback
from app.db.models.message import Message, MessageRole


async def diagnose():
    async with async_session_factory() as session:
        print("=" * 80)
        print("DIAGNOSIS: Knowledge Base State")
        print("=" * 80)
        
        # 1. Query all knowledge_base entries
        result = await session.execute(
            select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())
        )
        entries = result.scalars().all()
        print(f"\nTotal KB entries: {len(entries)}")
        for e in entries:
            print(f"\n--- KB Entry {e.id} ---")
            print(f"  question[:120]:  {e.question[:120] if e.question else 'NONE'}")
            print(f"  answer[:120]:    {e.answer[:120] if e.answer else 'NONE'}")
            print(f"  source_ticket_id: {e.source_ticket_id}")
            print(f"  is_active:       {e.is_active}")
            print(f"  created_at:      {e.created_at}")
            print(f"  has_embedding:   {e.embedding is not None}")
        
        # 2. Query fine-tuning entries specifically
        print("\n" + "=" * 80)
        print("FINE-TUNING SPECIFIC SEARCH")
        print("=" * 80)
        
        # Search by ILIKE
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.question.ilike('%fine%tuning%') | 
            KnowledgeBase.question.ilike('%finetuning%') |
            KnowledgeBase.answer.ilike('%fine%tuning%') | 
            KnowledgeBase.answer.ilike('%finetuning%')
        )
        result = await session.execute(stmt)
        ft_entries = result.scalars().all()
        print(f"\nEntries matching 'fine-tuning' or 'finetuning': {len(ft_entries)}")
        for e in ft_entries:
            print(f"\n--- KB Entry {e.id} ---")
            print(f"  question: {e.question[:200]}")
            print(f"  answer:   {e.answer[:200]}")
            print(f"  is_active: {e.is_active}")
        
        # 3. Check all tickets with their feedback/message/question
        print("\n" + "=" * 80)
        print("TICKETS WITH FEEDBACK/MESSAGE ANALYSIS")
        print("=" * 80)
        stmt = select(Ticket).order_by(Ticket.created_at.desc()).limit(20)
        result = await session.execute(stmt)
        tickets = result.scalars().all()
        
        for t in tickets:
            print(f"\n--- Ticket {t.id[:20]}... ---")
            print(f"  status:        {t.status}")
            print(f"  category:      {t.category}")
            print(f"  suggested_answer[:120]: {t.suggested_answer[:120] if t.suggested_answer else 'NONE'}")
            
            # Load feedback and its message
            if t.feedback_id:
                fb_result = await session.execute(
                    select(Feedback).where(Feedback.id == t.feedback_id)
                )
                fb = fb_result.scalar_one_or_none()
                if fb:
                    print(f"  feedback reason: {fb.reason[:100]}")
                    msg_result = await session.execute(
                        select(Message).where(Message.id == fb.message_id)
                    )
                    msg = msg_result.scalar_one_or_none()
                    if msg:
                        print(f"  DOWNVOTED MESSAGE (stored as KB question!): {msg.content[:120]}")
                        print(f"  message role: {msg.role}")
                        print(f"  *** THIS IS THE WRONG TEXT STORED AS KB question ***")
                        
                        # Find the actual user question
                        conv_msg_result = await session.execute(
                            select(Message).where(
                                Message.conversation_id == msg.conversation_id
                            ).order_by(Message.created_at)
                        )
                        conv_msgs = conv_msg_result.scalars().all()
                        user_q = ""
                        for cm in conv_msgs:
                            if cm.role == MessageRole.USER and cm.created_at < msg.created_at:
                                user_q = cm.content
                        print(f"  ACTUAL student question: {user_q[:150]}")
        
        # 4. Check for duplicate entries
        print("\n" + "=" * 80)
        print("DUPLICATE CHECK")
        print("=" * 80)
        
        # Check for same source_ticket_id
        dup_check = await session.execute(
            sqltext("""
                SELECT source_ticket_id, COUNT(*) as cnt
                FROM knowledge_base
                GROUP BY source_ticket_id
                HAVING COUNT(*) > 1
            """)
        )
        dup_rows = dup_check.fetchall()
        if dup_rows:
            print(f"\nDuplicate source_ticket_id entries found: {len(dup_rows)}")
            for row in dup_rows:
                print(f"  source_ticket_id={row.source_ticket_id}, count={row.cnt}")
        else:
            print("\nNo duplicate source_ticket_id entries found.")
        
        # Check for same question text
        dup_q = await session.execute(
            sqltext("""
                SELECT question, COUNT(*) as cnt
                FROM knowledge_base
                WHERE is_active = true
                GROUP BY question
                HAVING COUNT(*) > 1
            """)
        )
        dup_q_rows = dup_q.fetchall()
        if dup_q_rows:
            print(f"Duplicate question entries found: {len(dup_q_rows)}")
            for row in dup_q_rows:
                print(f"  question[:80]={row.question[:80]}, count={row.cnt}")
        else:
            print("No duplicate question entries found.")
    
    print("\n" + "=" * 80)
    print("DIAGNOSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(diagnose())
