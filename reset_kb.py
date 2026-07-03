"""Reset KB entries for clean migration re-run."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import select, delete
from app.db.session import async_session_factory
from app.db.models.knowledge_base import KnowledgeBase


async def reset():
    async with async_session_factory() as session:
        result = await session.execute(select(KnowledgeBase))
        entries = result.scalars().all()
        print(f"Deleting {len(entries)} KB entries...")
        for e in entries:
            await session.delete(e)
        await session.flush()
        await session.commit()
        print("Done. KB is now empty.")


if __name__ == "__main__":
    asyncio.run(reset())
