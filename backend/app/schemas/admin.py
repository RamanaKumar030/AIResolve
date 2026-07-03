from datetime import datetime
from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_users: int
    total_conversations: int
    total_messages: int
    total_tickets: int
    total_kb_entries: int
    tickets_by_status: dict[str, int]
    users_by_role: dict[str, int]
    recent_activity: list["ActivityItem"]


class ActivityItem(BaseModel):
    id: str
    user_name: str
    action: str
    resource: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserAdminResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    conversation_count: int = 0
    feedback_count: int = 0

    model_config = {"from_attributes": True}


class PaginatedResponse(BaseModel):
    items: list
    total: int
    skip: int
    limit: int
