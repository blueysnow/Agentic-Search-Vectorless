"""JSON extraction utilities -- adapted from reference pageindex/utils.py extract_json()."""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

# Matches a backslash NOT followed by a valid *structural* JSON escape character.
# Valid single-char JSON escapes: " \\ / b f n r t (plus u for \uXXXX).
# This regex is intentionally strict: it does NOT fix \f, \n, etc. to preserve
# valid JSON round-trips.  Use _fix_latex_backslashes_aggressive for LaTeX fallback.
_RE_INVALID_JSON_ESCAPE = re.compile(r'\\(?!["\\/bfnrtu])')

# Matches a backslash followed by any ASCII letter.  Used in the LaTeX-specific
# fallback path where we assume ALL \<letter> sequences are LaTeX commands (not
# JSON escape sequences), so they all need to be doubled.
_RE_LATEX_BACKSLASH = re.compile(r"\\([a-zA-Z])")


def _fix_latex_backslashes(json_content: str) -> str:
    """Escape bare LaTeX backslashes that are invalid JSON escapes.

    Replaces \\<char> where <char> is NOT a valid JSON escape character with
    \\\\<char>.  This handles LaTeX commands like \\geq, \\sqrt, \\alpha but
    deliberately leaves \\f, \\n, \\t, \\b, \\r alone (they are valid JSON).

    For the aggressive version that also escapes \\frac (\\f), use
    _fix_latex_backslashes_aggressive().
    """
    return _RE_INVALID_JSON_ESCAPE.sub(r"\\\\", json_content)


def _fix_latex_backslashes_aggressive(json_content: str) -> str:
    """Escape ALL bare backslash-letter sequences as LaTeX commands.

    Unlike _fix_latex_backslashes(), this also escapes \\f, \\n, \\t, \\b, \\r
    and similar sequences that are technically valid JSON escapes but semantically
    are LaTeX commands in LLM output (e.g. \\frac, \\nabla, \\tau).

    This is used as the final LaTeX fallback when the strict version still fails.
    """
    return _RE_LATEX_BACKSLASH.sub(r"\\\\\1", json_content)


def extract_json(content: str) -> dict | list | None:
    """Extract a JSON object/array from an LLM response.

    Handles ```json fences, Python None -> null, trailing commas, LaTeX backslashes, etc.
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

        # Keep a pristine copy of the extracted content for LaTeX fallback attempts.
        original_json_content = json_content

        # Try parsing as-is first (avoids mangling string values)
        try:
            return json.loads(json_content)
        except json.JSONDecodeError:
            pass

        # Clean Python literals only as fallback (matches reference None->null pattern)
        json_content = re.sub(r"\bNone\b", "null", json_content)
        json_content = re.sub(r"\bTrue\b", "true", json_content)
        json_content = re.sub(r"\bFalse\b", "false", json_content)

        try:
            return json.loads(json_content)
        except json.JSONDecodeError:
            pass

        # Remove trailing commas before ] or }
        try:
            cleaned = re.sub(r",\s*([}\]])", r"\1", json_content)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Apply aggressive LaTeX backslash fix to the ORIGINAL extracted content.
        # This escapes ALL \<letter> sequences as LaTeX commands (e.g. \frac, \geq,
        # \sqrt, \alpha, \nabla).  Using the aggressive form first handles the common
        # case where \f from \frac would otherwise be misread as a JSON form-feed.
        # This path is only reached after all standard parse attempts have failed.
        try:
            latex_aggressive = _fix_latex_backslashes_aggressive(original_json_content)
            return json.loads(latex_aggressive)
        except json.JSONDecodeError:
            pass

        # Strict fallback: only fix escapes that are strictly invalid in JSON
        # (i.e. NOT \f, \n, \t, \b, \r).  Rarely needed; kept for completeness.
        try:
            latex_fixed = _fix_latex_backslashes(original_json_content)
            return json.loads(latex_fixed)
        except json.JSONDecodeError:
            pass

        # Final attempt: Python literal cleanup AND aggressive LaTeX fix combined.
        try:
            combined = re.sub(r"\bNone\b", "null", original_json_content)
            combined = re.sub(r"\bTrue\b", "true", combined)
            combined = re.sub(r"\bFalse\b", "false", combined)
            combined = _fix_latex_backslashes_aggressive(combined)
            return json.loads(combined)
        except json.JSONDecodeError:
            pass

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
