import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SAEnum, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
import enum


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    feedback_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("feedback.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[TicketPriority] = mapped_column(
        SAEnum(TicketPriority, name="ticket_priority", create_constraint=True),
        default=TicketPriority.MEDIUM,
        nullable=False,
    )
    sentiment: Mapped[str] = mapped_column(String(100), nullable=False)
    root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_answer: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus, name="ticket_status", create_constraint=True),
        default=TicketStatus.OPEN,
        nullable=False,
    )
    reviewed_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(50), nullable=True)
    recommendation_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    conflicts_with_existing_kb: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    original_answer_was_accurate: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    original_answer_accuracy_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    feedback = relationship("Feedback", uselist=False,
                            foreign_keys=[feedback_id])
    knowledge_base_entries = relationship("KnowledgeBase", back_populates="ticket", cascade="all, delete-orphan")
