"""Tree generation: build hierarchical structures from document pages (ref: page_index.py:418-688).

Three modes:
  A. process_toc_with_page_numbers -- ToC found with page numbers
  B. process_toc_no_page_numbers -- ToC found but no page numbers
  C. process_no_toc -- No ToC, generate tree from scratch
"""

from __future__ import annotations

import copy
import json
import math

from src.llm.provider import LLMProvider, Message
from src.llm.prompts.tree_building import (
    PAGE_NUMBER_MAPPING_PROMPT,
    TREE_GENERATION_CONTINUE_PROMPT,
    TREE_GENERATION_INIT_PROMPT,
)
from src.utils.json_utils import extract_json
from src.utils.logger import get_logger
from src.utils.tokens import count_tokens

from .toc_transformer import toc_index_extractor, toc_transformer
from .tree_utils import convert_physical_index_to_int

logger = get_logger(__name__)


def page_list_to_group_text(
    page_list: list[tuple],
    max_tokens: int = 20000,
    start_index: int = 1,
) -> list[str]:
    """Split pages into token-limited groups with labeled tags (ref: page_index.py:418-451).

    Each page is wrapped in <physical_index_N> tags.
    Returns list of concatenated text groups.
    """
    page_contents: list[str] = []
    token_lengths: list[int] = []

    for i, (page_text, token_count) in enumerate(page_list):
        page_idx = start_index + i
        labeled = (
            f"<physical_index_{page_idx}>\n{page_text}\n<physical_index_{page_idx}>\n\n"
        )
        page_contents.append(labeled)
        token_lengths.append(count_tokens(labeled))

    total_tokens = sum(token_lengths)
    if total_tokens <= max_tokens:
        return ["".join(page_contents)]

    overlap_page = 1
    expected_parts = math.ceil(total_tokens / max_tokens)
    avg_tokens = math.ceil(((total_tokens / expected_parts) + max_tokens) / 2)

    subsets: list[str] = []
    current_subset: list[str] = []
    current_count = 0

    for i, (content, tokens) in enumerate(zip(page_contents, token_lengths)):
        if current_count + tokens > avg_tokens and current_subset:
            subsets.append("".join(current_subset))
            overlap_start = max(i - overlap_page, 0)
            current_subset = list(page_contents[overlap_start:i])
            current_count = sum(token_lengths[overlap_start:i])

        current_subset.append(content)
        current_count += tokens

    if current_subset:
        subsets.append("".join(current_subset))

    return subsets


def generate_toc_init(text_group: str, llm_provider: LLMProvider) -> list[dict]:
    """LLM generates initial tree from text (ref: page_index.py:534-566)."""
    prompt = TREE_GENERATION_INIT_PROMPT.format(text=text_group)
    response = llm_provider.chat([Message(role="user", content=prompt)])
    if response.finish_reason != "finished":
        raise RuntimeError(
            f"LLM did not finish tree generation: {response.finish_reason}"
        )
    result = extract_json(response.content)
    if result is None:
        raise ValueError("Failed to parse tree JSON from LLM response")
    return result


def generate_toc_continue(
    text_group: str,
    previous_structure: list[dict],
    llm_provider: LLMProvider,
) -> list[dict]:
    """LLM continues tree for next text group (ref: page_index.py:499-531)."""
    prompt = TREE_GENERATION_CONTINUE_PROMPT.format(
        text=text_group,
        previous_structure=json.dumps(previous_structure, indent=2),
    )
    response = llm_provider.chat([Message(role="user", content=prompt)])
    if response.finish_reason != "finished":
        raise RuntimeError(
            f"LLM did not finish tree continuation: {response.finish_reason}"
        )
    result = extract_json(response.content)
    if result is None:
        raise ValueError("Failed to parse continuation JSON from LLM response")
    return result


def add_page_number_to_toc(
    toc_json: list[dict],
    page_list: list[tuple],
    llm_provider: LLMProvider,
    start_index: int = 1,
    max_tokens: int = 20000,
) -> list[dict]:
    """LLM maps titles to physical pages (ref: page_index.py:453-483).

    Processes page groups sequentially, updating structure with physical indices.
    """
    group_texts = page_list_to_group_text(
        page_list, max_tokens=max_tokens, start_index=start_index
    )
    current_structure = copy.deepcopy(toc_json)

    for group_text in group_texts:
        prompt = PAGE_NUMBER_MAPPING_PROMPT.format(
            part=group_text,
            structure=json.dumps(current_structure, indent=2),
        )
        response = llm_provider.chat([Message(role="user", content=prompt)])
        result = extract_json(response.content)
        if result is not None:
            # Remove 'start' field added by LLM
            for item in result:
                item.pop("start", None)
            current_structure = result
        else:
            logger.warning(
                "add_page_number_parse_failed",
                group_index=group_texts.index(group_text),
            )

    return current_structure


def _extract_matching_page_pairs(
    toc_page: list[dict],
    toc_physical_index: list[dict],
    start_page_index: int,
) -> list[dict]:
    """Find matching title pairs between page-numbered and physically-indexed ToC."""
    pairs = []
    for phy_item in toc_physical_index:
        for page_item in toc_page:
            if phy_item.get("title") == page_item.get("title"):
                physical_index = phy_item.get("physical_index")
                try:
                    physical_index_int = (
                        int(physical_index) if physical_index is not None else None
                    )
                except (ValueError, TypeError):
                    physical_index_int = None
                if (
                    physical_index_int is not None
                    and physical_index_int >= start_page_index
                ):
                    pairs.append(
                        {
                            "title": phy_item.get("title"),
                            "page": page_item.get("page"),
                            "physical_index": physical_index,
                        }
                    )
    return pairs


def _calculate_page_offset(pairs: list[dict]) -> int | None:
    """Calculate the most common offset between physical_index and page number."""
    differences: list[int] = []
    for pair in pairs:
        try:
            differences.append(pair["physical_index"] - pair["page"])
        except (KeyError, TypeError):
            continue
    if not differences:
        return None
    counts: dict[int, int] = {}
    for d in differences:
        counts[d] = counts.get(d, 0) + 1
    return max(counts.items(), key=lambda x: x[1])[0]


def _remove_page_number(data: list[dict]) -> list[dict]:
    """Remove page_number field from all items."""
    for item in data:
        item.pop("page_number", None)
        item.pop("page", None)
    return data


def process_toc_with_page_numbers(
    toc_content: str,
    toc_json: list[dict] | None,
    page_list: list[tuple],
    llm_provider: LLMProvider,
    toc_page_list: list[int] | None = None,
    toc_check_pages: int = 20,
) -> list[dict]:
    """Mode A: ToC with page numbers (ref: page_index.py:614-643)."""
    toc_with_page = toc_transformer(toc_content, llm_provider)
    logger.info("toc_transformed", count=len(toc_with_page))

    # Get physical indices from first pages after ToC
    toc_no_page = copy.deepcopy(toc_with_page)
    _remove_page_number(toc_no_page)

    start_page_index = (toc_page_list[-1] + 1) if toc_page_list else 0
    toc_with_physical = toc_index_extractor(
        toc_no_page,
        page_list,
        llm_provider,
        start_page_index=start_page_index,
        num_pages=toc_check_pages,
    )
    toc_with_physical = convert_physical_index_to_int(toc_with_physical)

    # Calculate offset
    pairs = _extract_matching_page_pairs(
        toc_with_page, toc_with_physical, start_page_index + 1
    )
    offset = _calculate_page_offset(pairs)
    logger.info("page_offset_calculated", offset=offset)

    if offset is not None:
        for item in toc_with_page:
            if item.get("page") is not None and isinstance(item["page"], int):
                item["physical_index"] = item["page"] + offset
                del item["page"]

    return toc_with_page


def process_toc_no_page_numbers(
    toc_content: str,
    toc_json: list[dict] | None,
    page_list: list[tuple],
    llm_provider: LLMProvider,
) -> list[dict]:
    """Mode B: ToC without page numbers (ref: page_index.py:589-610)."""
    toc_structure = toc_transformer(toc_content, llm_provider)
    logger.info("toc_transformed_no_pages", count=len(toc_structure))

    result = add_page_number_to_toc(toc_structure, page_list, llm_provider)
    result = convert_physical_index_to_int(result)
    return result


def process_no_toc(
    page_list: list[tuple],
    llm_provider: LLMProvider,
    start_index: int = 1,
) -> list[dict]:
    """Mode C: No ToC found, generate tree from scratch (ref: page_index.py:568-587)."""
    group_texts = page_list_to_group_text(page_list, start_index=start_index)
    logger.info("generating_tree_no_toc", groups=len(group_texts))

    toc = generate_toc_init(group_texts[0], llm_provider)
    for group_text in group_texts[1:]:
        additional = generate_toc_continue(group_text, toc, llm_provider)
        toc.extend(additional)

    toc = convert_physical_index_to_int(toc)
    return toc
