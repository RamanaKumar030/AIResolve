from sqlalchemy import select, desc, text
from app.db.models.knowledge_base import KnowledgeBase
from app.repositories.base import BaseRepository


class KnowledgeBaseRepository(BaseRepository[KnowledgeBase]):
    def __init__(self, session):
        super().__init__(KnowledgeBase, session)

    async def search_similar(
        self, embedding: list[float], limit: int = 5, threshold: float = 0.7
    ) -> list[tuple[KnowledgeBase, float]]:
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
        try:
            stmt = text(
                """
                SELECT id, question, answer, source_ticket_id, is_active,
                       created_at, updated_at,
                       1 - (embedding::vector <=> CAST(:query_embedding AS vector)) AS similarity
                FROM knowledge_base
                WHERE is_active = true
                  AND embedding IS NOT NULL
                  AND 1 - (embedding::vector <=> CAST(:query_embedding2 AS vector)) > :threshold
                ORDER BY similarity DESC
                LIMIT :limit
                """
            )
            result = await self.session.execute(
                stmt,
                {
                    "query_embedding": embedding_str,
                    "query_embedding2": embedding_str,
                    "threshold": threshold,
                    "limit": limit,
                },
            )
            rows = result.fetchall()
        except Exception as e:
            logger = __import__('logging').getLogger(__name__)
            logger.warning("Vector similarity search failed: %s", e)
            rows = []

        entries = []
        for row in rows:
            entry = KnowledgeBase(
                id=row.id,
                question=row.question,
                answer=row.answer,
                source_ticket_id=row.source_ticket_id,
                is_active=row.is_active,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            entries.append((entry, float(row.similarity)))
        return entries

    async def get_active_entries(
        self, skip: int = 0, limit: int = 50
    ) -> list[KnowledgeBase]:
        stmt = (
            select(KnowledgeBase)
            .where(KnowledgeBase.is_active == True)
            .order_by(desc(KnowledgeBase.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_by_question(
        self, query: str, limit: int = 20
    ) -> list[KnowledgeBase]:
        stmt = (
            select(KnowledgeBase)
            .where(
                KnowledgeBase.is_active == True,
                KnowledgeBase.question.ilike(f"%{query}%"),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        exact = list(result.scalars().all())
        if exact:
            return exact

        # Word-level fallback: split query into words, find entries matching
        # at least 2 words (or 50% of query words, whichever is higher)
        words = [w for w in query.lower().split() if len(w) > 2]
        if len(words) < 2:
            return []

        from sqlalchemy import or_
        conditions = [KnowledgeBase.question.ilike(f"%{w}%") for w in words]
        stmt = (
            select(KnowledgeBase)
            .where(KnowledgeBase.is_active == True, or_(*conditions))
            .limit(limit * 2)
        )
        result = await self.session.execute(stmt)
        candidates = list(result.scalars().all())
        if not candidates:
            return []

        min_match = max(2, len(words) // 2)
        scored = []
        for c in candidates:
            c_lower = c.question.lower()
            match_count = sum(1 for w in words if w in c_lower)
            if match_count >= min_match:
                scored.append((match_count, c))
        scored.sort(key=lambda x: -x[0])
        return [c for _, c in scored[:limit]]
