import json
import logging
from typing import AsyncIterator
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.repositories.knowledge_base_repo import KnowledgeBaseRepository

logger = logging.getLogger(__name__)
settings = get_settings()

client = AsyncOpenAI(api_key=settings.openai_api_key)
MAX_CONTEXT_MESSAGES = 20


async def generate_embeddings(text: str) -> list[float]:
    response = await client.embeddings.create(
        model=settings.openai_embedding_model,
        input=text,
    )
    return response.data[0].embedding


async def generate_feedback_analysis(feedback_reason: str, question: str, answer: str) -> dict:
    prompt = f"""You are analyzing student feedback about an AI response.

Question: {question}
AI Answer: {answer}
Feedback Reason: {feedback_reason}

Provide a JSON analysis with these fields:
1. "category": The category of the issue (e.g., "incorrect_information", "incomplete_answer", "unclear_explanation", "off_topic", "other")
2. "priority": "low", "medium", "high", or "critical"
3. "sentiment": The sentiment of the feedback (e.g., "frustrated", "confused", "dissatisfied", "constructive")
4. "root_cause": A detailed analysis of what went wrong
5. "suggested_answer": An improved, corrected answer to the question
6. "recommendation": One of "recommend_approve", "recommend_reject", or "recommend_review". Use "recommend_approve" when the suggested answer is factually correct, complete, and directly addresses the issue. Use "recommend_reject" when the answer contains errors, is harmful, or cannot be salvaged. Use "recommend_review" when the question is subjective, ambiguous, or you are not fully confident.
7. "confidence_score": A number from 0 to 100 indicating how confident you are in this recommendation. Base this on factual verifiability, clarity of the issue, and completeness of the suggested fix.
8. "recommendation_reasoning": A JSON object with the following sub-fields:
   a. "factual_accuracy": Is the suggested answer factually correct? Explain briefly why or why not, citing what's right or wrong specifically.
   b. "addresses_root_cause": Does the suggested answer actually fix the specific problem the student flagged? Explain the connection explicitly (e.g. "yes, because the student said X was missing and this answer adds X").
   c. "completeness": Is anything still missing or oversimplified even in the suggested answer?
   d. "risk_if_wrong": If this recommendation is wrong, what's the impact? (e.g. "low — minor phrasing" or "high — factual claim about a date/number that could mislead many students")
   e. "summary": A concise 1-2 sentence summary of the recommendation reasoning.

Return ONLY valid JSON without markdown formatting. The "recommendation_reasoning" field must be a JSON object, not a string."""

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    result = json.loads(content)

    if isinstance(result.get("recommendation_reasoning"), str):
        try:
            result["recommendation_reasoning"] = json.loads(result["recommendation_reasoning"])
        except (json.JSONDecodeError, TypeError):
            result["recommendation_reasoning"] = {"summary": result.get("recommendation_reasoning", "")}

    return result


async def self_consistency_check(suggested_answer: str) -> dict:
    prompt = f"""You are a fact-checker. You are given ONLY the following suggested answer, with no additional context about the original question or feedback.

Suggested Answer: {suggested_answer}

Independently assess this answer for factual correctness. Do not rely on any prior reasoning — evaluate it fresh.

Return a JSON object with:
1. "independent_confidence_score": A number from 0 to 100 rating how confident you are that this answer is factually correct.
2. "issues_found": A list of any factual issues, inaccuracies, or unsupported claims found (empty list if none).
3. "verdict": "correct", "partially_correct", or "incorrect"

Return ONLY valid JSON without markdown formatting."""

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    return json.loads(content)


async def verify_original_answer(question: str, answer: str) -> dict:
    prompt = f"""You are an independent fact-checker. You are given a question and an AI-generated answer. Your job is to assess the ORIGINAL answer on its own merits — completely ignore any student complaint, feedback, or external opinion about the answer.

Question: {question}
AI Answer: {answer}

Independently assess: is this answer factually accurate? Answer based ONLY on your own knowledge, not on any external framing.

Return a JSON object with:
1. "original_answer_was_accurate": true or false. true if the answer is factually correct, complete enough for the question asked, and not misleading. false if it contains factual errors, is significantly misleading, or is completely wrong.
2. "original_answer_accuracy_reasoning": A concise explanation of why the answer is or is not accurate, citing specific facts.
3. "feedback_is_vague_claim": true or false. true if the student's complaint (not provided here) would effectively be a vague/generic claim like "wrong", "fake", "bad" without identifying a specific, verifiable gap. Since you don't have the complaint text, set this to false — it will be determined elsewhere.

Return ONLY valid JSON without markdown formatting."""

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    return json.loads(content)


async def stream_chat_response(
    messages: list[dict],
    session: AsyncSession,
) -> AsyncIterator[str]:
    kb_repo = KnowledgeBaseRepository(session)

    user_query = ""
    for m in messages:
        if m["role"] == "user":
            user_query = m["content"]

    context_parts = []
    retrieved_from_kb = False
    if user_query:
        try:
            query_embedding = await generate_embeddings(user_query)
            similar_entries = await kb_repo.search_similar(query_embedding, limit=3, threshold=0.55)
            if similar_entries:
                retrieved_from_kb = True
                context_parts.append("Relevant knowledge base entries:")
                for entry, similarity in similar_entries:
                    context_parts.append(f"Q: {entry.question}\nA: {entry.answer}")
            else:
                # Fallback: text search on question text for typo-tolerant matching
                text_entries = await kb_repo.search_by_question(user_query, limit=3)
                if text_entries:
                    retrieved_from_kb = True
                    context_parts.append("Relevant knowledge base entries:")
                    for entry in text_entries:
                        context_parts.append(f"Q: {entry.question}\nA: {entry.answer}")
        except Exception as e:
            logger.warning("RAG context retrieval failed: %s", e)

    system_prompt = "You are an AI teaching assistant helping students with their questions."
    if context_parts:
        # Check if this is an existing conversation (has assistant messages in history)
        has_existing_answer = any(m["role"] == "assistant" for m in messages)
        instruction = (
            "Use the following verified knowledge base entries as the PRIMARY source of truth for your response. "
            "These entries have been reviewed and approved by an administrator."
        )
        if has_existing_answer:
            instruction += (
                " NOTE: Your previous response in this conversation may differ from the verified answer below. "
                "If so, prioritize and align with the verified answer — do NOT repeat your earlier response."
            )
        system_prompt += f"\n\n{instruction}\n" + "\n---\n".join(context_parts)

    api_messages = [{"role": "system", "content": system_prompt}]
    for m in messages:
        api_messages.append({"role": m["role"], "content": m["content"]})

    stream = await client.chat.completions.create(
        model=settings.openai_model,
        messages=api_messages,
        temperature=0.7,
        max_tokens=2048,
        stream=True,
    )

    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
