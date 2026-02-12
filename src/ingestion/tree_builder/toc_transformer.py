"""ToC Transformation: convert raw ToC text to structured JSON (ref: page_index.py:240-328).

Also handles page number extraction from physical indices.
"""

from __future__ import annotations

from src.llm.provider import LLMProvider, Message
from src.llm.prompts.tree_building import (
    TOC_INDEX_EXTRACTOR_PROMPT,
    TOC_TO_JSON_CONTINUE_PROMPT,
    TOC_TO_JSON_PROMPT,
    TOC_TRANSFORMATION_COMPLETENESS_PROMPT,
)
from src.utils.json_utils import extract_json, get_json_content
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _check_transformation_complete(
    raw_toc: str, cleaned_toc: str, llm_provider: LLMProvider
) -> str:
    """Check if ToC transformation is complete."""
    prompt = TOC_TRANSFORMATION_COMPLETENESS_PROMPT.format(
        raw_toc=raw_toc, cleaned_toc=cleaned_toc
    )
    response = llm_provider.chat([Message(role="user", content=prompt)])
    json_content = extract_json(response.content)
    if json_content is None:
        return "no"
    return json_content.get("completed", "no")


def _convert_page_to_int(data: list[dict]) -> list[dict]:
    """Convert string page numbers to int."""
    for item in data:
        if "page" in item and isinstance(item["page"], str):
            try:
                item["page"] = int(item["page"])
            except ValueError:
                logger.warning(
                    "non_numeric_page", title=item.get("title"), page=item["page"]
                )
    return data


def toc_transformer(toc_content: str, llm_provider: LLMProvider) -> list[dict]:
    """Convert ToC text to JSON with continuation for long ToCs (ref: page_index.py:270-328).

    Returns list of dicts with structure, title, page keys.
    """
    prompt = TOC_TO_JSON_PROMPT.format(toc_content=toc_content)
    response = llm_provider.chat([Message(role="user", content=prompt)])
    last_complete = response.content

    is_complete = _check_transformation_complete(
        toc_content, last_complete, llm_provider
    )
    if is_complete == "yes" and response.finish_reason == "finished":
        parsed = extract_json(last_complete)
        if parsed is None:
            raise ValueError("Failed to parse ToC JSON from LLM response")
        if isinstance(parsed, dict) and "table_of_contents" in parsed:
            return _convert_page_to_int(parsed["table_of_contents"])
        if isinstance(parsed, list):
            return _convert_page_to_int(parsed)
        raise ValueError("Unexpected ToC JSON structure")

    # Continue for long ToCs
    last_complete = get_json_content(last_complete)
    max_continuations = 5
    for _ in range(max_continuations):
        # Trim to last complete entry
        position = last_complete.rfind("}")
        if position != -1:
            last_complete = last_complete[: position + 2]

        cont_prompt = TOC_TO_JSON_CONTINUE_PROMPT.format(
            toc_content=toc_content,
            incomplete_json=last_complete,
        )
        cont_response = llm_provider.chat([Message(role="user", content=cont_prompt)])
        new_part = cont_response.content

        if new_part.startswith("```json"):
            new_part = get_json_content(new_part)
        last_complete = last_complete + new_part

        is_complete = _check_transformation_complete(
            toc_content, last_complete, llm_provider
        )
        if is_complete == "yes" and cont_response.finish_reason == "finished":
            break

    parsed = extract_json(last_complete)
    if parsed is None:
        raise ValueError("Failed to parse ToC JSON after continuation")
    if isinstance(parsed, dict) and "table_of_contents" in parsed:
        return _convert_page_to_int(parsed["table_of_contents"])
    if isinstance(parsed, list):
        return _convert_page_to_int(parsed)
    raise ValueError("Unexpected ToC JSON structure after continuation")


def toc_index_extractor(
    toc_json: list[dict],
    page_list: list[tuple],
    llm_provider: LLMProvider,
    start_page_index: int = 0,
    num_pages: int = 20,
) -> list[dict]:
    """Map ToC page numbers to physical pages (ref: page_index.py:240-266).

    Builds labeled page content and asks LLM to map sections.
    """
    main_content = ""
    end = min(start_page_index + num_pages, len(page_list))
    for page_index in range(start_page_index, end):
        main_content += (
            f"<physical_index_{page_index + 1}>\n"
            f"{page_list[page_index][0]}\n"
            f"<physical_index_{page_index + 1}>\n\n"
        )

    prompt = TOC_INDEX_EXTRACTOR_PROMPT.format(toc=str(toc_json), content=main_content)
    response = llm_provider.chat([Message(role="user", content=prompt)])
    result = extract_json(response.content)
    if result is None:
        logger.warning("toc_index_extractor_parse_failed", toc_count=len(toc_json))
        return toc_json
    return result
