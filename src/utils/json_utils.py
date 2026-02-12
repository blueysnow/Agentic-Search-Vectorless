"""JSON extraction utilities -- adapted from reference pageindex/utils.py extract_json()."""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)


def extract_json(content: str) -> dict | list | None:
    """Extract a JSON object/array from an LLM response.

    Handles ```json fences, Python None -> null, trailing commas, etc.
    Adapted directly from the reference utils.py extract_json().

    Returns None on failure so callers can distinguish parse failure from empty JSON.
    """
    try:
        # Try to extract JSON enclosed within ```json ... ```
        start_idx = content.find("```json")
        if start_idx != -1:
            start_idx += 7
            end_idx = content.rfind("```")
            json_content = content[start_idx:end_idx].strip()
        else:
            # Fallback: look for first { or [ and its matching close
            json_content = content.strip()
            brace = json_content.find("{")
            bracket = json_content.find("[")
            if brace == -1 and bracket == -1:
                return None
            if brace == -1:
                start = bracket
            elif bracket == -1:
                start = brace
            else:
                start = min(brace, bracket)
            json_content = json_content[start:]
            # Find matching close bracket/brace
            open_char = json_content[0]
            close_char = "}" if open_char == "{" else "]"
            last_close = json_content.rfind(close_char)
            if last_close != -1:
                json_content = json_content[: last_close + 1]

        # Try parsing as-is first (avoids mangling string values)
        try:
            return json.loads(json_content)
        except json.JSONDecodeError:
            pass

        # Clean Python literals only as fallback (matches reference None->null pattern)
        json_content = re.sub(r"\bNone\b", "null", json_content)
        json_content = re.sub(r"\bTrue\b", "true", json_content)
        json_content = re.sub(r"\bFalse\b", "false", json_content)

        return json.loads(json_content)
    except json.JSONDecodeError:
        try:
            # Remove trailing commas before ] or }
            cleaned = re.sub(r",\s*([}\]])", r"\1", json_content)
            return json.loads(cleaned)
        except Exception:
            logger.error("Failed to parse JSON even after cleanup")
            return None
    except Exception as exc:
        logger.error("Unexpected error extracting JSON: %s", exc)
        return None


def get_json_content(response: str) -> str:
    """Strip ```json fences and return the raw JSON string.

    Directly adapted from reference get_json_content().
    """
    start_idx = response.find("```json")
    if start_idx != -1:
        response = response[start_idx + 7 :]

    end_idx = response.rfind("```")
    if end_idx != -1:
        response = response[:end_idx]

    return response.strip()
