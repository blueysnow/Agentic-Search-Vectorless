"""Tree verification: verify and fix ToC page assignments (ref: page_index.py:731-944).

Sample-based verification with async concurrent checking and fix loops.
"""

from __future__ import annotations

import asyncio
import random

from src.llm.provider import LLMProvider, Message
from src.llm.prompts.verification import (
    SINGLE_TOC_ITEM_FIXER_PROMPT,
    TITLE_AT_START_PROMPT,
    TITLE_VERIFICATION_PROMPT,
)
from src.utils.json_utils import extract_json
from src.utils.logger import get_logger
from .tree_utils import convert_physical_index_to_int

logger = get_logger(__name__)


async def check_title_appearance(
    title: str,
    page_text: str,
    llm_provider: LLMProvider,
) -> str:
    """LLM verifies title appears on page (ref: page_index.py:731-786).

    Returns 'yes' or 'no'.
    """
    prompt = TITLE_VERIFICATION_PROMPT.format(title=title, page_text=page_text)
    response = await llm_provider.chat_async([Message(role="user", content=prompt)])
    json_content = extract_json(response.content)
    if json_content is None:
        return "no"
    return json_content.get("answer", "no")


async def check_title_appearance_in_start(
    title: str,
    page_text: str,
    llm_provider: LLMProvider,
) -> str:
    """Check if title appears at the beginning of a page (ref: page_index.py:48-71).

    Returns 'yes' or 'no'.
    """
    prompt = TITLE_AT_START_PROMPT.format(title=title, page_text=page_text)
    response = await llm_provider.chat_async([Message(role="user", content=prompt)])
    json_content = extract_json(response.content)
    if json_content is None:
        return "no"
    return json_content.get("start_begin", "no")


async def _check_title_appearance_in_start_concurrent(
    structure: list[dict],
    page_list: list[tuple],
    llm_provider: LLMProvider,
) -> list[dict]:
    """Check appear_start for all items concurrently."""
    for item in structure:
        if item.get("physical_index") is None:
            item["appear_start"] = "no"

    tasks = []
    valid_items = []
    for item in structure:
        if item.get("physical_index") is not None:
            page_idx = item["physical_index"] - 1
            if 0 <= page_idx < len(page_list):
                page_text = page_list[page_idx][0]
                tasks.append(
                    check_title_appearance_in_start(
                        item["title"], page_text, llm_provider
                    )
                )
                valid_items.append(item)
            else:
                item["appear_start"] = "no"

    results = await asyncio.gather(*tasks, return_exceptions=True)
    exception_count = 0
    for item, result in zip(valid_items, results):
        if isinstance(result, Exception):
            exception_count += 1
            logger.error("check_start_failed", title=item["title"], error=str(result))
            item["appear_start"] = "no"
        else:
            item["appear_start"] = result

    if results and exception_count > len(results) / 2:
        logger.error(
            "check_start_majority_failed",
            total=len(results),
            exceptions=exception_count,
        )

    return structure


async def verify_toc(
    structure: list[dict],
    page_list: list[tuple],
    llm_provider: LLMProvider,
    sample_rate: float = 0.2,
) -> tuple[float, list[dict]]:
    """Sample ~20% verification of title-page assignments (ref: page_index.py:892-944).

    Returns (accuracy, list_of_incorrect_items).
    """
    # Filter items with valid physical_index
    valid_items = [
        (i, item)
        for i, item in enumerate(structure)
        if item.get("physical_index") is not None
    ]

    if not valid_items:
        return 0.0, []

    # Check if last physical_index covers enough of the document
    last_phys = max(item.get("physical_index", 0) for _, item in valid_items)
    if last_phys < len(page_list) / 2:
        return 0.0, []

    # Sample
    n = max(1, int(len(valid_items) * sample_rate))
    n = min(n, len(valid_items))
    sampled = random.sample(valid_items, n)

    # Run checks concurrently
    tasks = []
    for idx, item in sampled:
        page_idx = item["physical_index"] - 1
        if 0 <= page_idx < len(page_list):
            page_text = page_list[page_idx][0]
        else:
            page_text = ""
        tasks.append(check_title_appearance(item["title"], page_text, llm_provider))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    correct = 0
    exception_count = 0
    incorrect: list[dict] = []
    for (idx, item), result in zip(sampled, results):
        if isinstance(result, Exception):
            exception_count += 1
            incorrect.append(
                {
                    "list_index": idx,
                    "title": item["title"],
                    "physical_index": item.get("physical_index"),
                }
            )
        elif result == "yes":
            correct += 1
        else:
            incorrect.append(
                {
                    "list_index": idx,
                    "title": item["title"],
                    "physical_index": item.get("physical_index"),
                }
            )

    if results and exception_count > len(results) / 2:
        logger.error(
            "verify_toc_majority_failed", total=len(results), exceptions=exception_count
        )
        return 0.0, incorrect

    accuracy = correct / len(results) if results else 0.0
    logger.info(
        "verification_result",
        accuracy=accuracy,
        checked=len(results),
        incorrect=len(incorrect),
    )
    return accuracy, incorrect


def _single_toc_item_fixer(
    title: str,
    content: str,
    llm_provider: LLMProvider,
) -> int | None:
    """Fix a single incorrect ToC item by searching surrounding pages."""
    prompt = SINGLE_TOC_ITEM_FIXER_PROMPT.format(title=title, content=content)
    response = llm_provider.chat([Message(role="user", content=prompt)])
    json_content = extract_json(response.content)
    if json_content is None:
        return None
    raw = json_content.get("physical_index")
    if raw is None:
        return None
    result = convert_physical_index_to_int(raw)
    if isinstance(result, int):
        return result
    return None


async def fix_incorrect_toc(
    structure: list[dict],
    page_list: list[tuple],
    llm_provider: LLMProvider,
    max_rounds: int = 3,
) -> list[dict]:
    """Fix loop: verify, fix incorrect items, repeat (ref: page_index.py:870-886).

    Modifies structure in place and returns it.
    """
    _, incorrect = await verify_toc(structure, page_list, llm_provider, sample_rate=1.0)

    for round_num in range(max_rounds):
        if not incorrect:
            break

        logger.info("fix_round", round=round_num + 1, incorrect_count=len(incorrect))
        incorrect_indices = {item["list_index"] for item in incorrect}

        for item in incorrect:
            idx = item["list_index"]
            if idx < 0 or idx >= len(structure):
                continue

            # Find surrounding correct boundaries
            prev_correct = 1
            for j in range(idx - 1, -1, -1):
                if (
                    j not in incorrect_indices
                    and structure[j].get("physical_index") is not None
                ):
                    prev_correct = structure[j]["physical_index"]
                    break

            next_correct = len(page_list)
            for j in range(idx + 1, len(structure)):
                if (
                    j not in incorrect_indices
                    and structure[j].get("physical_index") is not None
                ):
                    next_correct = structure[j]["physical_index"]
                    break

            # Build page content for search range
            page_contents = []
            for page_idx in range(prev_correct, next_correct + 1):
                list_idx = page_idx - 1
                if 0 <= list_idx < len(page_list):
                    page_contents.append(
                        f"<physical_index_{page_idx}>\n{page_list[list_idx][0]}\n<physical_index_{page_idx}>\n\n"
                    )
            content_range = "".join(page_contents)

            fixed = _single_toc_item_fixer(item["title"], content_range, llm_provider)
            if fixed is not None:
                structure[idx]["physical_index"] = fixed

        # Re-verify
        _, incorrect = await verify_toc(
            structure, page_list, llm_provider, sample_rate=1.0
        )

    return structure
