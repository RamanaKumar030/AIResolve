import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.feedback_service import FeedbackService
from app.services.ticket_service import TicketService
from app.schemas.feedback import (
    VoteRequest,
    FeedbackCreateRequest,
    FeedbackResponse,
)
from app.api.deps import get_current_user
from app.db.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/vote/{message_id}")
async def vote_message(
    message_id: str,
    body: VoteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.vote_type not in ("upvote", "downvote"):
        raise HTTPException(
            status_code=400, detail="vote_type must be 'upvote' or 'downvote'"
        )
    feedback_service = FeedbackService(db)
    result = await feedback_service.toggle_vote(
        message_id, current_user.id, body.vote_type
    )
    return result


@router.post("/submit", response_model=FeedbackResponse)
async def submit_feedback(
    body: FeedbackCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    feedback_service = FeedbackService(db)
    existing = await feedback_service.get_user_feedback(
        body.message_id, current_user.id
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="Already submitted feedback for this message"
        )

    feedback = await feedback_service.submit_feedback(
        body.message_id, current_user.id, body.reason
    )

    try:
        ticket_service = TicketService(db)
        ticket = await ticket_service.create_ticket_from_feedback(feedback.id)
        if ticket:
            feedback.ticket_id = ticket.id
            await db.flush()
    except Exception as e:
        logger.error("Failed to create ticket for feedback %s: %s", feedback.id, e)

    return FeedbackResponse.model_validate(feedback)
