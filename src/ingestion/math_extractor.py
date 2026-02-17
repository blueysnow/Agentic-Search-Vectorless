"""Math detection utilities for LLM-processed text and LaTeX source.

This module detects LaTeX math delimiters in text that has ALREADY been processed
(e.g. LLM output, LaTeX source files).  It does NOT attempt to find math in raw
PDF output where no delimiters exist.

Design: pure-function, stateless, no side effects, no external dependencies beyond
the standard library ``re`` module.  Safe to import anywhere without triggering
config loading or database connections.
"""

from __future__ import annotations

import re

# --- Compiled regex patterns (module-level for performance) ---

# Block math: $$...$$ (match first to avoid counting $$ as two inline delimiters)
_RE_BLOCK = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)

# Inline math: $...$ but NOT $$...$$
# Negative lookbehind/ahead ensures we do not match the $ chars inside $$ blocks.
_RE_INLINE = re.compile(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", re.DOTALL)

# LaTeX equation environments: \begin{equation}, \begin{align}, \begin{gather},
# \begin{multline} (with optional * suffix for unnumbered variants).
_RE_ENV = re.compile(r"\\begin\{(equation|align|gather|multline)\*?\}")


def has_math(text: str) -> bool:
    """Return True if *text* contains LaTeX math delimiters.

    Detects:
    - Inline math: ``$...$`` (excluding ``$$``)
    - Block math: ``$$...$$``
    - Equation environments: ``\\begin{equation|align|gather|multline}``

    Returns False for empty string, None, plain text, raw PDF garbled output, and
    text that contains only currency ``$`` signs without math content.
    """
    if not text:
        return False
    # Block math check comes first so $$ is not misidentified as two inline $.
    if _RE_BLOCK.search(text):
        return True
    if _RE_ENV.search(text):
        return True
    if _RE_INLINE.search(text):
        return True
    return False


def detect_math_regions(text: str) -> dict:
    """Return a summary of math regions found in *text*.

    Returns a dict with keys:

    - ``has_math`` (bool): True if any math was detected.
    - ``inline_count`` (int): number of non-overlapping ``$...$`` matches.
    - ``block_count`` (int): number of non-overlapping ``$$...$$`` matches.
    - ``equation_env_count`` (int): number of ``\\begin{...}`` environment opens.

    The block pattern is matched first and its spans are excluded from the inline
    count to avoid double-counting.
    """
    if not text:
        return {"has_math": False, "inline_count": 0, "block_count": 0, "equation_env_count": 0}

    block_matches = _RE_BLOCK.findall(text)
    block_count = len(block_matches)

    # Remove block math spans from the text before counting inline to avoid overlap.
    text_without_blocks = _RE_BLOCK.sub("", text)
    inline_matches = _RE_INLINE.findall(text_without_blocks)
    inline_count = len(inline_matches)

    env_matches = _RE_ENV.findall(text)
    env_count = len(env_matches)

    found = block_count > 0 or inline_count > 0 or env_count > 0
    return {
        "has_math": found,
        "inline_count": inline_count,
        "block_count": block_count,
        "equation_env_count": env_count,
    }
