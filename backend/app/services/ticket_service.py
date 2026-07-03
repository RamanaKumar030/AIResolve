import json
import logging
import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.feedback_repo import FeedbackRepository
from app.repositories.ticket_repo import TicketRepository
from app.repositories.message_repo import MessageRepository
from app.repositories.knowledge_base_repo import KnowledgeBaseRepository
from app.db.models.ticket import Ticket, TicketStatus
from app.db.models.feedback import Feedback
from app.db.models.message import MessageRole
from app.db.models.system_setting import SystemSetting
from app.db.models.user import User, UserRole
from app.services.openai_service import (
    generate_feedback_analysis,
    generate_embeddings,
    self_consistency_check,
    verify_original_answer,
)

logger = logging.getLogger(__name__)

_VAGUE_CLAIM_PATTERNS = [
    "wrong", "fake", "incorrect", "bad", "terrible", "useless",
    "not good", "doesn't work", "not working", "garbage",
    "horrible", "stupid", "nonsense", "not true", "lie",
]


def _is_vague_claim(reason: str) -> bool:
    reason_lower = reason.lower().strip()
    if not reason_lower or len(reason_lower) < 5:
        return True

    # Quality descriptors — describe WHAT is wrong with the answer (specific & actionable)
    quality_descriptors = {
        "incomplete", "outdated", "missing", "brief", "short", "vague",
        "shallow", "basic", "superficial", "confusing", "unclear",
        "contradictory", "obsolete", "overly", "verbose",
        "repetitive", "irrelevant", "offtopic",
    }
    specific_indicators = {
        "missing", "example", "detail", "explain", "specific",
        "instead", "because", "should", "need", "please", "add",
        "clarify", "expand", "elaborate", "source", "citation",
        "reference", "refer", "more", "include", "why", "how",
    }
    vague_insults = {
        "fake", "bad", "garbage", "stupid", "nonsense", "useless",
        "terrible", "horrible", "rubbish", "trash", "bullshit",
        "fabrication", "not good", "doesn't work", "not working",
        "not true", "lie", "lol", "lmao", "wrong", "incorrect",
    }
    filler_words = {
        "this", "that", "is", "are", "was", "were", "the", "a", "an",
        "it", "its", "my", "your", "so", "very", "too", "really",
        "just", "but", "and", "or", "for", "with", "completely",
        "totally", "absolutely", "simply", "basically", "literally",
    }

    # Single-word reason: check if it's a quality descriptor or specific
    words = reason_lower.split()
    if len(words) == 1:
        word = words[0].strip(".!? ")
        if word in vague_insults:
            return True
        if word in quality_descriptors:
            return False
        # If it's not obviously specific, treat as vague
        return True

    # Multi-word: has any specific indicator? If so, not vague
    if any(indicator in reason_lower for indicator in specific_indicators):
        return False
    if any(qd in reason_lower for qd in quality_descriptors):
        return False

    # Strip filler words and check if remaining meaningful words are insults
    meaningful = {w.strip(".!? ") for w in words
                  if len(w.strip(".!? ")) > 2 and w.strip(".!? ") not in filler_words}
    if meaningful and meaningful.issubset(vague_insults):
        return True

    # Check if there's specific factual content (numbers, dates, domain terms)
    import re as _re
    has_specific_content = bool(_re.search(r"\d+", reason_lower))  # contains numbers
    # Check if meaningful words are actually English-like (have vowels, not keyboard smashes)
    _vowels = set("aeiou")
    real_words = {w for w in meaningful - vague_insults if any(c in _vowels for c in w) and len(w) > 2}
    has_specific_content = has_specific_content or len(real_words) >= 2
    has_specific_content = has_specific_content or any(len(w) > 8 for w in real_words)

    # Check if ANY word is a vague insult — BUT only flag as vague if
    # the feedback LACKS specific factual content (numbers, domain terms, etc.)
    if not has_specific_content and any(w.strip(".!? ") in vague_insults for w in words):
        return True

    # Short generic complaint without specifics
    if len(words) <= 3 and not has_specific_content:
        return True

    return False


def _detect_and_neutralize_injection(feedback_reason: str, analysis: dict) -> dict:
    """Server-side validation of AI analysis output against prompt injection.
    
    Checks if the analysis output matches values that were commanded by the 
    untrusted user feedback text. If injection is detected, overrides the
    compromised values with safe defaults.
    """
    reason_lower = feedback_reason.lower()
    result = dict(analysis)

    # Extract any demanded confidence number from the feedback
    import re
    confidence_matches = re.findall(r"(\d{1,3})\s*%", reason_lower)
    demanded_confidences = [int(m) for m in confidence_matches if 0 <= int(m) <= 100]

    current_conf = result.get("confidence_score")
    if current_conf is not None and demanded_confidences:
        # If analysis confidence matches a value the feedback demanded, flag it
        if current_conf in demanded_confidences:
            logger.warning(
                "Injection detected: analysis confidence %.0f matches demanded value(s) %s in feedback '%s'",
                current_conf, demanded_confidences, feedback_reason[:80],
            )
            # Cap confidence — the AI may have been instructed to output this value
            result["confidence_score"] = min(current_conf, 50)

    # Check if the feedback commands a specific recommendation
    demanded_recommend = None
    approve_phrases = ["recommend_approve", "as approved", "mark.*approved", "auto-?approve"]
    reject_phrases = ["recommend_reject", "as rejected", "mark.*rejected"]
    for phrase in approve_phrases:
        if re.search(phrase, reason_lower):
            demanded_recommend = "recommend_approve"
            break
    if not demanded_recommend:
        for phrase in reject_phrases:
            if re.search(phrase, reason_lower):
                demanded_recommend = "recommend_reject"
                break

    current_rec = result.get("recommendation")
    if demanded_recommend and current_rec == demanded_recommend:
        logger.warning(
            "Injection detected: analysis recommendation '%s' matches demanded value in feedback '%s' — routing to review",
            current_rec, feedback_reason[:80],
        )
        result["recommendation"] = "recommend_review"
        result["confidence_score"] = min(current_conf or 50, 50)

    # Check if feedback demands a specific category value
    demanded_cat = None
    valid_categories = {"incorrect_information", "incomplete_answer", "unclear_explanation", "off_topic", "other"}
    cat_match = re.search(r"(?:\"category\"|category).*?\"(\w+)\"", reason_lower)
    if cat_match and cat_match.group(1) in valid_categories:
        demanded_cat = cat_match.group(1)
    current_cat = result.get("category")
    if demanded_cat and current_cat == demanded_cat:
        logger.warning(
            "Injection detected: analysis category '%s' matches demanded value in feedback",
            current_cat,
        )
        result["category"] = "other"

    return result


AUTO_CLEAR_DENYLIST_CATEGORIES = [
    "safety",
    "medical",
    "legal",
    "academic_integrity",
    "exam_answer",
    "health_advice",
]

_SENSITIVE_TOPIC_KEYWORDS = {
    "dosage", "dose", "mg/", "medication", "prescription", "overdose", "side effect",
    "contraindication", "symptom", "diagnosis", "treatment", "therapy", "surgery",
    "doctor", "physician", "patient", "clinical", "therapeutic", "pharmaceutical",
    "copyright", "lawsuit", "attorney", "lawyer", "illegal", "legal", "court",
    "exam", "test answer", "homework", "assignment", "cheat", "plagiarism",
    "quiz", "final exam", "midterm",
}


def _has_sensitive_topic(question: str, answer: str) -> bool:
    """Check if the question or answer involves a sensitive topic that should
    never be auto-cleared (medical, legal, academic integrity, etc.)."""
    combined = (question + " " + answer).lower()
    for keyword in _SENSITIVE_TOPIC_KEYWORDS:
        if keyword in combined:
            return True
    return False


class TicketService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.feedback_repo = FeedbackRepository(session)
        self.ticket_repo = TicketRepository(session)
        self.message_repo = MessageRepository(session)

    async def create_ticket_from_feedback(self, feedback_id: str) -> Ticket | None:
        feedback = await self.feedback_repo.get(feedback_id)
        if not feedback:
            logger.warning("Feedback %s not found", feedback_id)
            return None

        message = await self.message_repo.get(feedback.message_id)
        if not message:
            logger.warning("Message for feedback %s not found", feedback_id)
            return None

        conversation_messages = await self.message_repo.get_conversation_messages(
            message.conversation_id
        )

        question = ""
        for m in conversation_messages:
            if m.role == MessageRole.USER and m.created_at < message.created_at:
                question = m.content
            if m.id == message.id:
                break

        original_verification = None
        try:
            original_verification = await verify_original_answer(
                question=question or "Unknown question",
                answer=message.content,
            )
        except Exception as e:
            logger.warning("Original answer verification failed: %s", e)

        original_answer_was_accurate = None
        original_answer_accuracy_reasoning = None
        if original_verification:
            original_answer_was_accurate = original_verification.get("original_answer_was_accurate")
            original_answer_accuracy_reasoning = original_verification.get("original_answer_accuracy_reasoning")

        analysis = await generate_feedback_analysis(
            feedback_reason=feedback.reason,
            question=question or "Unknown question",
            answer=message.content,
        )

        recommendation = analysis.get("recommendation")
        recommendation_reasoning = analysis.get("recommendation_reasoning")
        confidence_score = analysis.get("confidence_score")

        if isinstance(recommendation_reasoning, dict):
            recommendation_reasoning = json.dumps(recommendation_reasoning)

        # Server-side injection detection: check if the analysis output matches
        # values that were demanded in the untrusted feedback text. This catches
        # cases where prompt injection bypassed the LLM guardrails.
        analysis = _detect_and_neutralize_injection(feedback.reason, analysis)

        recommendation = analysis.get("recommendation", recommendation)
        confidence_score = analysis.get("confidence_score", confidence_score)

        # Decision logic: if original answer was independently verified as accurate,
        # reject the ticket to prevent unnecessary KB changes. Two cases:
        # 1. Vague/non-specific claim (e.g. "fake", "wrong" with no details)
        # 2. Specific false factual assertion (e.g. "it was 1944 not 1945")
        # In both cases, the original answer needs no correction.
        should_reject = False
        reject_reason = ""

        if original_answer_was_accurate is True:
            if _is_vague_claim(feedback.reason):
                should_reject = True
                reject_reason = "The original answer was factually accurate. Student's feedback was a vague/non-specific claim without identifying a verifiable gap."
            else:
                # Check if the feedback claims a factual error (even with specifics)
                accuracy_claim_words = {"wrong", "incorrect", "inaccurate", "error", "mistake",
                                        "false", "fake", "not true", "lie", "fabrication"}
                claims_error = any(w in feedback.reason.lower() for w in accuracy_claim_words)
                if claims_error:
                    should_reject = True
                    reject_reason = "The original answer was factually accurate. Student's feedback contains a factual error claim but independent verification confirmed the original answer is correct."

        if should_reject:
            logger.info(
                "Original answer verified accurate, feedback '%s' — overriding to recommend_reject: %s",
                feedback.reason[:50], reject_reason,
            )
            recommendation = "recommend_reject"
            ticket = await self.ticket_repo.create(
                feedback_id=feedback_id,
                category=analysis.get("category", "other"),
                priority=analysis.get("priority", "medium"),
                sentiment=analysis.get("sentiment", "neutral"),
                root_cause=reject_reason,
                suggested_answer=analysis.get("suggested_answer", message.content),
                recommendation=recommendation,
                recommendation_reasoning=recommendation_reasoning,
                confidence_score=min(confidence_score, 50) if confidence_score else 30,
                original_answer_was_accurate=original_answer_was_accurate,
                original_answer_accuracy_reasoning=original_answer_accuracy_reasoning,
            )
        else:
            ticket = await self.ticket_repo.create(
                feedback_id=feedback_id,
                category=analysis["category"],
                priority=analysis.get("priority", "medium"),
                sentiment=analysis.get("sentiment", "neutral"),
                root_cause=analysis["root_cause"],
                suggested_answer=analysis["suggested_answer"],
                recommendation=recommendation,
                recommendation_reasoning=recommendation_reasoning,
                confidence_score=confidence_score,
                original_answer_was_accurate=original_answer_was_accurate,
                original_answer_accuracy_reasoning=original_answer_accuracy_reasoning,
            )

        await self.feedback_repo.update(feedback_id, ticket_id=ticket.id)

        logger.info(
            "Created ticket %s for feedback %s (category=%s, priority=%s, recommendation=%s, confidence=%s)",
            ticket.id, feedback_id, analysis["category"], analysis.get("priority"),
            recommendation, confidence_score,
        )

        try:
            await self._try_auto_clear(ticket)
        except Exception as e:
            logger.error("Auto-clear check failed for ticket %s: %s", ticket.id, e)

        return ticket

    async def _try_auto_clear(self, ticket: Ticket) -> None:
        setting = await self.session.get(SystemSetting, "auto_clear_enabled")
        if not setting or setting.value != "true":
            return

        if ticket.recommendation == "recommend_review":
            logger.info("Auto-clear skipped for %s: recommend_review", ticket.id)
            return

        if ticket.recommendation not in ("recommend_approve", "recommend_reject"):
            logger.info("Auto-clear skipped for %s: unknown recommendation %s", ticket.id, ticket.recommendation)
            return

        if ticket.confidence_score is None or ticket.confidence_score < 70:
            if ticket.recommendation == "recommend_approve":
                logger.info("Auto-clear skipped for %s: confidence %s < 70 for approve", ticket.id, ticket.confidence_score)
                return

        if hasattr(ticket, "category") and ticket.category:
            category_lower = ticket.category.lower().replace(" ", "_")
            for denied in AUTO_CLEAR_DENYLIST_CATEGORIES:
                if denied in category_lower:
                    logger.info(
                        "Auto-clear skipped for %s: denylisted category '%s'",
                        ticket.id, ticket.category,
                    )
                    return

        # Sensitive topic gate: check if the question involves medical, legal,
        # or academic integrity topics — never auto-clear these.
        try:
            question = await self._get_ticket_question(ticket)
            sensitive = _has_sensitive_topic(question or "", ticket.suggested_answer or "")
            if sensitive:
                logger.info(
                    "Auto-clear skipped for %s: sensitive topic detected in question '%s'",
                    ticket.id, (question or "")[:60],
                )
                return
        except Exception as e:
            logger.warning("Sensitive topic check failed for %s: %s", ticket.id, e)

        # Self-consistency check: verify the suggested answer independently
        try:
            consistency = await self_consistency_check(ticket.suggested_answer)
        except Exception as e:
            logger.warning("Self-consistency check failed for %s: %s", ticket.id, e)
            consistency = {"independent_confidence_score": 0}

        independent_score = consistency.get("independent_confidence_score", 0)
        original_score = ticket.confidence_score or 0

        if (ticket.original_answer_was_accurate is not True
                and abs(independent_score - original_score) > 15
                and ticket.recommendation == "recommend_approve"):
            logger.info(
                "Auto-clear skipped for %s: confidence divergence %s vs %s (delta=%s > 15)",
                ticket.id, original_score, independent_score,
                abs(independent_score - original_score),
            )
            return

        await self._execute_auto_clear(
            ticket, consistency,
            independent_score=independent_score,
        )

    async def _execute_auto_clear(
        self,
        ticket: Ticket,
        consistency_result: dict,
        independent_score: float,
        conflict_detail: list | None = None,
    ) -> None:
        from datetime import datetime, timezone

        stmt = select(User).where(User.role == UserRole.ADMIN).limit(1)
        result = await self.session.execute(stmt)
        admin_user = result.scalar_one_or_none()
        if not admin_user:
            logger.error("Cannot auto-clear ticket %s: no admin user found", ticket.id)
            return

        new_status = TicketStatus.APPROVED if ticket.recommendation == "recommend_approve" else TicketStatus.REJECTED

        # For approval: write to KB BEFORE updating ticket status.
        # If the KB write fails, do NOT change the ticket status.
        if new_status == TicketStatus.APPROVED:
            from app.services.knowledge_base_service import KnowledgeBaseService
            kb_service = KnowledgeBaseService(self.session)
            try:
                await kb_service.add_from_ticket(ticket.id)
            except Exception as e:
                logger.error(
                    "Auto-clear KB insert failed for %s: %s — ticket will remain open",
                    ticket.id, e,
                )
                return

        await self.ticket_repo.update(
            ticket.id,
            status=new_status,
            reviewed_by=admin_user.id,
            reviewed_at=datetime.now(timezone.utc),
        )

        reasoning = {}
        if ticket.recommendation_reasoning:
            try:
                reasoning = json.loads(ticket.recommendation_reasoning)
            except (json.JSONDecodeError, TypeError):
                reasoning = {"summary": ticket.recommendation_reasoning}

        from app.services.audit_service import AuditService
        audit_service = AuditService(self.session)
        await audit_service.log(
            user_id=admin_user.id,
            action="ticket_auto_cleared",
            resource="ticket",
            resource_id=ticket.id,
            details={
                "auto_cleared_by": "ai",
                "recommendation": ticket.recommendation,
                "status": new_status.value,
                "original_confidence_score": ticket.confidence_score,
                "independent_confidence_score": independent_score,
                "recommendation_reasoning": reasoning,
                "self_consistency_verdict": consistency_result.get("verdict"),
                "self_consistency_issues": consistency_result.get("issues_found", []),
                "conflict_detected": conflict_detail is not None and len(conflict_detail or []) > 0,
                "conflict_details": conflict_detail,
                "category_gate_passed": True,
            },
        )

        if new_status == TicketStatus.APPROVED:
            await audit_service.log(
                user_id=admin_user.id,
                action="add_to_knowledge_base",
                resource="knowledge_base",
                resource_id=ticket.id,
                details={"source": "auto_clear", "ticket_id": ticket.id},
            )
            logger.info("Auto-clear approved ticket %s and added to KB", ticket.id)
        else:
            logger.info("Auto-clear rejected ticket %s", ticket.id)

    async def _get_ticket_question(self, ticket: Ticket) -> str | None:
        """Retrieve the original user question that triggered the AI answer."""
        try:
            from app.db.models.feedback import Feedback
            from app.db.models.message import Message
            if ticket.feedback_id:
                feedback = await self.session.get(Feedback, ticket.feedback_id)
                if feedback and feedback.message_id:
                    msg = await self.session.get(Message, feedback.message_id)
                    if msg:
                        return msg.content
        except Exception:
            pass
        return None

    async def get_ticket(self, ticket_id: str) -> Ticket | None:
        return await self.ticket_repo.get(ticket_id)

    async def get_all_tickets(
        self, skip: int = 0, limit: int = 50
    ) -> list[Ticket]:
        return await self.ticket_repo.get_all(skip, limit)

    async def review_ticket(
        self, ticket_id: str, admin_id: str, status: str, review_notes: str | None = None
    ) -> Ticket | None:
        from datetime import datetime, timezone
        ticket = await self.ticket_repo.get(ticket_id)
        if not ticket:
            return None

        new_status = TicketStatus(status)
        update_data = {
            "status": new_status,
            "reviewed_by": admin_id,
            "reviewed_at": datetime.now(timezone.utc),
        }
        return await self.ticket_repo.update(ticket_id, **update_data)

    async def get_ticket_stats(self) -> dict:
        return await self.ticket_repo.get_stats()
