import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.knowledge_base_service import KnowledgeBaseService
from app.schemas.knowledge_base import (
    KnowledgeBaseResponse,
    KnowledgeBaseSearchResult,
    KnowledgeBaseUpdateRequest,
)
from app.api.deps import get_admin_user, get_current_user
from app.db.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/entries", response_model=list[KnowledgeBaseResponse])
async def list_entries(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb_service = KnowledgeBaseService(db)
    entries = await kb_service.get_all_entries(skip, limit)
    return [KnowledgeBaseResponse.model_validate(e) for e in entries]


@router.get("/search", response_model=list[KnowledgeBaseSearchResult])
async def search_kb(
    q: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kb_service = KnowledgeBaseService(db)
    results = await kb_service.search_similar(q, limit=limit)
    return [
        KnowledgeBaseSearchResult(
            id=entry.id,
            question=entry.question,
            answer=entry.answer,
            similarity=round(similarity, 4),
            source_ticket_id=entry.source_ticket_id,
        )
        for entry, similarity in results
    ]


@router.patch("/entries/{entry_id}", response_model=KnowledgeBaseResponse)
async def update_entry(
    entry_id: str,
    body: KnowledgeBaseUpdateRequest,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    kb_service = KnowledgeBaseService(db)
    update_data = body.model_dump(exclude_unset=True)
    entry = await kb_service.update_entry(entry_id, **update_data)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return KnowledgeBaseResponse.model_validate(entry)


@router.delete("/entries/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: str,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    kb_service = KnowledgeBaseService(db)
    deleted = await kb_service.delete_entry(entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entry not found")
