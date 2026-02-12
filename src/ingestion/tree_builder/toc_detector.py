"""Table of Contents detection (ref: page_index.py:104-724).

Detects ToC pages, extracts ToC text, checks for page numbers.
"""

from __future__ import annotations

import re

from src.llm.provider import LLMProvider, Message
from src.llm.prompts.toc_detection import (
    PAGE_NUMBER_DETECTION_PROMPT,
    TOC_CONTINUATION_PROMPT,
    TOC_DETECTION_PROMPT,
    TOC_EXTRACTION_COMPLETENESS_PROMPT,
    TOC_EXTRACTION_PROMPT,
)
from src.utils.json_utils import extract_json
from src.utils.logger import get_logger

logger = get_logger(__name__)


def toc_detector_single_page(page_text: str, llm_provider: LLMProvider) -> str:
    """LLM checks one page for ToC presence (ref: page_index.py:104-122).

    Returns 'yes' or 'no'.
    """
    prompt = TOC_DETECTION_PROMPT.format(content=page_text)
    response = llm_provider.chat([Message(role="user", content=prompt)])
    json_content = extract_json(response.content)
    if json_content is None:
        return "no"
    return json_content.get("toc_detected", "no")


def find_toc_pages(
    page_list: list[tuple],
    llm_provider: LLMProvider,
    max_pages: int = 20,
) -> list[int]:
    """Scan first N pages for ToC (ref: page_index.py:333-358).

    Returns 0-indexed page indices that contain ToC.
    """
    toc_page_list: list[int] = []
    last_page_is_yes = False

    for i in range(len(page_list)):
        if i >= max_pages and not last_page_is_yes:
            break

        detected = toc_detector_single_page(page_list[i][0], llm_provider)
        if detected == "yes":
            logger.info("toc_detected", page=i)
            toc_page_list.append(i)
            last_page_is_yes = True
        elif detected == "no" and last_page_is_yes:
            logger.info("toc_ended", last_toc_page=i - 1)
            break

    return toc_page_list


def _check_toc_extraction_complete(
    content: str, toc: str, llm_provider: LLMProvider
) -> str:
    """Check if extracted ToC is complete."""
    prompt = TOC_EXTRACTION_COMPLETENESS_PROMPT.format(content=content, toc=toc)
    response = llm_provider.chat([Message(role="user", content=prompt)])
    json_content = extract_json(response.content)
    if json_content is None:
        return "no"
    return json_content.get("completed", "no")


def extract_toc_content(
    page_list: list[tuple],
    toc_pages: list[int],
    llm_provider: LLMProvider,
) -> str:
    """Extract ToC text with continuation for long ToCs (ref: page_index.py:160-197).

    Combines ToC page text, asks LLM to extract, continues if incomplete.
    """
    raw_toc_text = ""
    for page_index in toc_pages:
        raw_toc_text += page_list[page_index][0]

    prompt = TOC_EXTRACTION_PROMPT.format(content=raw_toc_text)
    messages = [Message(role="user", content=prompt)]
    response = llm_provider.chat(messages)
    result = response.content

    is_complete = _check_toc_extraction_complete(raw_toc_text, result, llm_provider)
    if is_complete == "yes" and response.finish_reason == "finished":
        return result

    # Continue extraction
    max_continuations = 5
    for _ in range(max_continuations):
        cont_messages = [
            Message(role="user", content=prompt),
            Message(role="assistant", content=result),
            Message(role="user", content=TOC_CONTINUATION_PROMPT),
        ]
        cont_response = llm_provider.chat(cont_messages)
        result = result + cont_response.content
        is_complete = _check_toc_extraction_complete(raw_toc_text, result, llm_provider)
        if is_complete == "yes" and cont_response.finish_reason == "finished":
            break

    return result


def detect_page_index(toc_text: str, llm_provider: LLMProvider) -> str:
    """Check if page numbers are present in ToC (ref: page_index.py:199-217).

    Returns 'yes' or 'no'.
    """
    prompt = PAGE_NUMBER_DETECTION_PROMPT.format(toc_content=toc_text)
    response = llm_provider.chat([Message(role="user", content=prompt)])
    json_content = extract_json(response.content)
    if json_content is None:
        return "no"
    return json_content.get("page_index_given_in_toc", "no")


def toc_extractor(
    page_list: list[tuple],
    toc_pages: list[int],
    llm_provider: LLMProvider,
) -> dict:
    """Combined extraction: get ToC text and check for page numbers (ref: page_index.py:219-235).

    Returns dict with 'toc_content' and 'page_index_given_in_toc'.
    """
    # Transform dots to colons (like reference)
    toc_content = ""
    for page_index in toc_pages:
        toc_content += page_list[page_index][0]
    toc_content = re.sub(r"\.{5,}", ": ", toc_content)
    toc_content = re.sub(r"(?:\. ){5,}\.?", ": ", toc_content)

    has_page_index = detect_page_index(toc_content, llm_provider)

    return {
        "toc_content": toc_content,
        "page_index_given_in_toc": has_page_index,
    }


def check_toc(
    page_list: list[tuple],
    llm_provider: LLMProvider,
    max_pages: int = 20,
) -> dict:
    """Main entry point for ToC detection (ref: page_index.py:688-724).

    Returns dict with toc_content, toc_page_list, page_index_given_in_toc.
    """
    toc_page_list = find_toc_pages(page_list, llm_provider, max_pages=max_pages)

    if not toc_page_list:
        logger.info("no_toc_found")
        return {
            "toc_content": None,
            "toc_page_list": [],
            "page_index_given_in_toc": "no",
        }

    logger.info("toc_found", pages=toc_page_list)
    toc_json = toc_extractor(page_list, toc_page_list, llm_provider)

    if toc_json["page_index_given_in_toc"] == "yes":
        logger.info("page_index_found_in_toc")
        return {
            "toc_content": toc_json["toc_content"],
            "toc_page_list": toc_page_list,
            "page_index_given_in_toc": "yes",
        }

    # Search for additional ToC sections with page indices
    current_start = toc_page_list[-1] + 1
    while current_start < len(page_list) and current_start < max_pages:
        additional_pages = find_toc_pages(
            page_list[current_start:],
            llm_provider,
            max_pages=max_pages - current_start,
        )
        if not additional_pages:
            break
        # Adjust indices back to absolute
        additional_pages = [p + current_start for p in additional_pages]
        additional_toc = toc_extractor(page_list, additional_pages, llm_provider)
        if additional_toc["page_index_given_in_toc"] == "yes":
            return {
                "toc_content": additional_toc["toc_content"],
                "toc_page_list": additional_pages,
                "page_index_given_in_toc": "yes",
            }
        current_start = additional_pages[-1] + 1

    logger.info("page_index_not_found_in_toc")
    return {
        "toc_content": toc_json["toc_content"],
        "toc_page_list": toc_page_list,
        "page_index_given_in_toc": "no",
    }
