"""Node and document summarization (ref: utils.py:605-658)."""

from __future__ import annotations

import asyncio

from src.llm.provider import LLMProvider, Message
from src.llm.prompts.summarization import DOC_DESCRIPTION_PROMPT, NODE_SUMMARY_PROMPT
from src.ingestion.tree_builder.tree_utils import structure_to_list
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def generate_node_summary(node_text: str, llm_provider: LLMProvider) -> str:
    """Generate a summary for a single node's text (ref: utils.py:605-613)."""
    prompt = NODE_SUMMARY_PROMPT.format(node_text=node_text)
    response = await llm_provider.chat_async([Message(role="user", content=prompt)])
    return response.content


async def generate_summaries_for_structure(
    structure: dict | list,
    llm_provider: LLMProvider,
) -> dict | list:
    """Generate summaries for all nodes in parallel via asyncio.gather (ref: utils.py:616-623)."""
    nodes = structure_to_list(structure)
    tasks = [
        generate_node_summary(node.get("text", ""), llm_provider) for node in nodes
    ]
    summaries = await asyncio.gather(*tasks, return_exceptions=True)

    for node, summary in zip(nodes, summaries):
        if isinstance(summary, Exception):
            logger.error(
                "node_summary_failed", title=node.get("title"), error=str(summary)
            )
            node["summary"] = ""
        else:
            node["summary"] = summary

    return structure


def generate_doc_description(structure: dict | list, llm_provider: LLMProvider) -> str:
    """Generate a one-sentence document description (ref: utils.py:649-658)."""

    # Build clean structure without text
    def _clean(s: dict | list) -> dict | list:
        if isinstance(s, dict):
            clean: dict = {}
            for key in ("title", "node_id", "summary"):
                if key in s:
                    clean[key] = s[key]
            if "nodes" in s and s["nodes"]:
                clean["nodes"] = _clean(s["nodes"])
            return clean
        elif isinstance(s, list):
            return [_clean(item) for item in s]
        return s

    clean_struct = _clean(structure)
    prompt = DOC_DESCRIPTION_PROMPT.format(structure=clean_struct)
    response = llm_provider.chat([Message(role="user", content=prompt)])
    return response.content
