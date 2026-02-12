"""LLM reasoner -- sufficiency check, answer generation, cross-ref following (plan section 7.1 step 5).

Iteratively checks if retrieved content is sufficient to answer the query.
If not, recommends next action: navigate_deeper, follow_reference, or search_different_section.
"""

from __future__ import annotations

import logging

from src.llm.prompts.sufficiency_check import (
    MULTI_TURN_SUFFICIENCY_PROMPT,
    SUFFICIENCY_CHECK_PROMPT,
)
from src.llm.provider import LLMProvider, Message
from src.models.retrieval import NextAction, ReasonerResponse
from src.utils.json_utils import extract_json

logger = logging.getLogger(__name__)

VALID_ACTION_TYPES = frozenset(
    {"navigate_deeper", "follow_reference", "search_different_section"}
)


def _parse_reasoner_response(raw: str) -> ReasonerResponse:
    """Parse LLM JSON output into a ReasonerResponse.

    Returns a safe default on parse failure.
    """
    parsed = extract_json(raw)
    if parsed is None or not isinstance(parsed, dict):
        logger.warning("reasoner_parse_failed", extra={"raw": raw[:200]})
        return ReasonerResponse(
            answer=None,
            confidence=0.0,
            sufficient=False,
            next_action=None,
        )

    # Parse confidence safely
    try:
        confidence = float(parsed.get("confidence", 0.0))
    except (ValueError, TypeError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    # Parse next_action
    next_action_raw = parsed.get("nextAction")
    next_action: NextAction | None = None
    if isinstance(next_action_raw, dict):
        action_type = next_action_raw.get("type", "")
        if action_type in VALID_ACTION_TYPES:
            next_action = NextAction(
                type=action_type,
                target_node_id=str(next_action_raw.get("targetNodeId", "")),
                reasoning=str(next_action_raw.get("reasoning", "")),
            )

    answer = parsed.get("answer")
    if answer is not None:
        answer = str(answer)

    return ReasonerResponse(
        answer=answer,
        confidence=confidence,
        sufficient=bool(parsed.get("sufficient", False)),
        next_action=next_action,
    )


async def check_sufficiency(
    query: str,
    content: str,
    ancestor_context: str,
    cross_ref_text: str,
    llm_provider: LLMProvider,
) -> ReasonerResponse:
    """Check if the provided content is sufficient to answer the query.

    Returns a ReasonerResponse with answer (if sufficient) or next_action.
    """
    if not content.strip():
        return ReasonerResponse(
            answer=None,
            confidence=0.0,
            sufficient=False,
            next_action=None,
        )

    prompt = SUFFICIENCY_CHECK_PROMPT.format(
        query=query,
        content=content,
        ancestor_context=ancestor_context,
        cross_refs=cross_ref_text,
    )

    try:
        response = await llm_provider.chat_async(
            [Message(role="user", content=prompt)],
            temperature=0.0,
        )
    except Exception:
        logger.exception("reasoner_llm_failed")
        return ReasonerResponse(
            answer=None,
            confidence=0.0,
            sufficient=False,
            next_action=None,
        )

    return _parse_reasoner_response(response.content)


async def check_sufficiency_multi_turn(
    query: str,
    content: str,
    ancestor_context: str,
    conversation_history: str,
    llm_provider: LLMProvider,
) -> ReasonerResponse:
    """Check sufficiency with conversation history for multi-turn."""
    if not content.strip():
        return ReasonerResponse(
            answer=None,
            confidence=0.0,
            sufficient=False,
            next_action=None,
        )

    prompt = MULTI_TURN_SUFFICIENCY_PROMPT.format(
        conversation_history=conversation_history,
        query=query,
        content=content,
        ancestor_context=ancestor_context,
    )

    try:
        response = await llm_provider.chat_async(
            [Message(role="user", content=prompt)],
            temperature=0.0,
        )
    except Exception:
        logger.exception("reasoner_multi_turn_llm_failed")
        return ReasonerResponse(
            answer=None,
            confidence=0.0,
            sufficient=False,
            next_action=None,
        )

    return _parse_reasoner_response(response.content)
