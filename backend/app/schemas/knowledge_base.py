from datetime import datetime
from pydantic import BaseModel


class KnowledgeBaseResponse(BaseModel):
    id: str
    question: str
    answer: str
    source_ticket_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeBaseSearchResult(BaseModel):
    id: str
    question: str
    answer: str
    similarity: float
    source_ticket_id: str

    model_config = {"from_attributes": True}


class KnowledgeBaseUpdateRequest(BaseModel):
    question: str | None = None
    answer: str | None = None
    is_active: bool | None = None
