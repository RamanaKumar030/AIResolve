from datetime import datetime
from pydantic import BaseModel


class VoteRequest(BaseModel):
    vote_type: str


class VoteResponse(BaseModel):
    id: str
    message_id: str
    vote_type: str
    created_at: datetime


class FeedbackCreateRequest(BaseModel):
    message_id: str
    reason: str


class FeedbackResponse(BaseModel):
    id: str
    message_id: str
    reason: str
    ticket_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedbackDetailResponse(BaseModel):
    id: str
    message_id: str
    user_id: str
    user_name: str = ""
    reason: str
    ticket_id: str | None
    created_at: datetime
    ticket: "TicketResponse | None" = None

    model_config = {"from_attributes": True}


class TicketResponse(BaseModel):
    id: str
    feedback_id: str
    category: str
    priority: str
    sentiment: str
    root_cause: str
    suggested_answer: str
    status: str
    reviewed_by: str | None
    reviewed_at: datetime | None
    recommendation: str | None = None
    recommendation_reasoning: str | None = None
    confidence_score: float | None = None
    conflicts_with_existing_kb: bool | None = None
    original_answer_was_accurate: bool | None = None
    original_answer_accuracy_reasoning: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketReviewRequest(BaseModel):
    status: str
    review_notes: str | None = None
