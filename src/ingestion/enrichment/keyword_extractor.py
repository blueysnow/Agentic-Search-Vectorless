"""Keyword extraction for nodes."""

from __future__ import annotations

from src.llm.provider import LLMProvider, Message
from src.llm.prompts.summarization import KEYWORD_EXTRACTION_PROMPT
from src.utils.json_utils import extract_json
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def extract_keywords(node_text: str, llm_provider: LLMProvider) -> list[str]:
    """Extract 3-8 keywords from node text."""
    if not node_text.strip():
        return []
    prompt = KEYWORD_EXTRACTION_PROMPT.format(node_text=node_text)
    response = await llm_provider.chat_async([Message(role="user", content=prompt)])
    result = extract_json(response.content)
    if isinstance(result, list):
        return [str(kw) for kw in result[:8]]
    return []
