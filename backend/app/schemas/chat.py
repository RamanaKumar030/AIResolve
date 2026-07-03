from datetime import datetime
from pydantic import BaseModel


class SendMessageRequest(BaseModel):
    conversation_id: str | None = None
    content: str


class SendMessageResponse(BaseModel):
    message_id: str
    conversation_id: str
    content: str
    role: str
    created_at: datetime


class ConversationResponse(BaseModel):
    id: str
    title: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime
    vote: str | None = None
    feedback: str | None = None

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    id: str
    title: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse]

    model_config = {"from_attributes": True}


class ConversationCreateRequest(BaseModel):
    title: str = "New Conversation"


class StreamEvent(BaseModel):
    type: str
    content: str | None = None
    conversation_id: str | None = None
    message_id: str | None = None
    error: str | None = None
