import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models.user import User, UserRole
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.db.models.ticket import Ticket, TicketStatus
from app.db.models.feedback import Feedback
from app.db.models.knowledge_base import KnowledgeBase
from app.db.models.audit_log import AuditLog
from app.db.models.system_setting import SystemSetting
from app.schemas.admin import DashboardStats, UserAdminResponse
from app.schemas.feedback import FeedbackDetailResponse, TicketResponse, TicketReviewRequest
from app.api.deps import get_admin_user
from app.services.ticket_service import TicketService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.audit_service import AuditService
from app.repositories.feedback_repo import FeedbackRepository
from app.repositories.ticket_repo import TicketRepository

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    user_count = await db.scalar(select(func.count()).select_from(User))
    conv_count = await db.scalar(select(func.count()).select_from(Conversation))
    msg_count = await db.scalar(select(func.count()).select_from(Message))
    ticket_count = await db.scalar(select(func.count()).select_from(Ticket))
    kb_count = await db.scalar(select(func.count()).select_from(KnowledgeBase))

    ticket_repo = TicketRepository(db)
    ticket_stats = await ticket_repo.get_stats()

    student_count = await db.scalar(
        select(func.count()).where(User.role == UserRole.STUDENT)
    )
    admin_count = await db.scalar(
        select(func.count()).where(User.role == UserRole.ADMIN)
    )

    audit_service = AuditService(db)
    recent = await audit_service.get_recent(10)
    activity = [
        {
            "id": log.id,
            "user_name": log.user.full_name if log.user else "Unknown",
            "action": log.action,
            "resource": log.resource,
            "created_at": log.created_at.isoformat(),
        }
        for log in recent
    ]

    return DashboardStats(
        total_users=user_count or 0,
        total_conversations=conv_count or 0,
        total_messages=msg_count or 0,
        total_tickets=ticket_count or 0,
        total_kb_entries=kb_count or 0,
        tickets_by_status=ticket_stats,
        users_by_role={"student": student_count or 0, "admin": admin_count or 0},
        recent_activity=activity,
    )


@router.get("/users", response_model=list[UserAdminResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: str | None = None,
    search: str | None = None,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == UserRole(role))
    if search:
        stmt = stmt.where(
            User.full_name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%")
        )
    stmt = stmt.order_by(desc(User.created_at)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()

    response = []
    for user in users:
        conv_count = await db.scalar(
            select(func.count()).where(Conversation.user_id == user.id)
        )
        feedback_count = await db.scalar(
            select(func.count()).where(Feedback.user_id == user.id)
        )
        response.append(
            UserAdminResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role.value,
                is_active=user.is_active,
                created_at=user.created_at,
                conversation_count=conv_count or 0,
                feedback_count=feedback_count or 0,
            )
        )
    return response


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    body: dict,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    new_role = body.get("role")
    if new_role not in ("student", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = UserRole(new_role)
    await db.flush()

    audit_service = AuditService(db)
    await audit_service.log(
        user_id=admin_user.id,
        action="update_role",
        resource="user",
        resource_id=user_id,
        details={"new_role": new_role},
    )
    return {"status": "ok"}


@router.patch("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: str,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = not user.is_active
    await db.flush()

    audit_service = AuditService(db)
    await audit_service.log(
        user_id=admin_user.id,
        action="toggle_active",
        resource="user",
        resource_id=user_id,
        details={"is_active": user.is_active},
    )
    return {"is_active": user.is_active}


@router.get("/feedback", response_model=list[FeedbackDetailResponse])
async def list_feedback(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    feedback_repo = FeedbackRepository(db)
    feedbacks = await feedback_repo.get_all_with_tickets(skip, limit)
    result = []
    for fb in feedbacks:
        ticket_data = None
        if fb.ticket:
            ticket_data = TicketResponse.model_validate(fb.ticket)
        result.append(
            FeedbackDetailResponse(
                id=fb.id,
                message_id=fb.message_id,
                user_id=fb.user_id,
                user_name=fb.user.full_name if fb.user else "",
                reason=fb.reason,
                ticket_id=fb.ticket_id,
                created_at=fb.created_at,
                ticket=ticket_data,
            )
        )
    return result


@router.get("/tickets", response_model=list[TicketResponse])
async def list_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: str | None = None,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    ticket_repo = TicketRepository(db)
    if status:
        try:
            s = TicketStatus(status)
            tickets = await ticket_repo.get_by_status(s, skip, limit)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    else:
        tickets = await ticket_repo.get_all(skip, limit)
    return [TicketResponse.model_validate(t) for t in tickets]


@router.post("/tickets/{ticket_id}/review", response_model=TicketResponse)
async def review_ticket(
    ticket_id: str,
    body: TicketReviewRequest,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    if body.status not in ("approved", "rejected", "in_review"):
        raise HTTPException(status_code=400, detail="Invalid status")

    ticket_service = TicketService(db)
    ticket = await ticket_service.review_ticket(
        ticket_id, admin_user.id, body.status, body.review_notes
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    audit_service = AuditService(db)
    await audit_service.log(
        user_id=admin_user.id,
        action="review_ticket",
        resource="ticket",
        resource_id=ticket_id,
        details={"status": body.status},
    )

    if ticket.status == TicketStatus.APPROVED:
        kb_service = KnowledgeBaseService(db)
        await kb_service.add_from_ticket(ticket.id)
        await audit_service.log(
            user_id=admin_user.id,
            action="add_to_knowledge_base",
            resource="knowledge_base",
            resource_id=ticket.id,
        )

    return TicketResponse.model_validate(ticket)


@router.get("/tickets/stats")
async def get_ticket_stats(
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    ticket_service = TicketService(db)
    return await ticket_service.get_ticket_stats()


@router.get("/audit-logs")
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "user_name": log.user.full_name if log.user else "Unknown",
            "action": log.action,
            "resource": log.resource,
            "resource_id": log.resource_id,
            "details": log.details,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


@router.get("/settings/{key}")
async def get_setting(
    key: str,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    setting = await db.get(SystemSetting, key)
    return {"key": key, "value": setting.value if setting else None}


@router.put("/settings/{key}")
async def update_setting(
    key: str,
    body: dict,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    value = body.get("value", "")
    setting = await db.get(SystemSetting, key)
    if setting:
        setting.value = str(value)
    else:
        setting = SystemSetting(key=key, value=str(value))
        db.add(setting)
    await db.flush()

    audit_service = AuditService(db)
    await audit_service.log(
        user_id=admin_user.id,
        action="update_setting",
        resource="system_setting",
        resource_id=key,
        details={"key": key, "value": str(value)},
    )

    return {"key": key, "value": str(value)}
