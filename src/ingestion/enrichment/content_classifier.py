"""Content type classification based on title and text patterns."""

from __future__ import annotations

import re

# Title patterns mapped to content types
_TITLE_PATTERNS = [
    (re.compile(r"^appendix\b", re.IGNORECASE), "appendix"),
    (re.compile(r"^(?:table\s+of\s+contents|contents)$", re.IGNORECASE), "toc"),
    (re.compile(r"^(?:table|tbl)\s+\d", re.IGNORECASE), "table"),
    (re.compile(r"^(?:figure|fig)\s+\d", re.IGNORECASE), "figure"),
    (re.compile(r"^(?:preface|foreword|prologue)$", re.IGNORECASE), "preface"),
    (
        re.compile(r"^(?:bibliography|references|works\s+cited)$", re.IGNORECASE),
        "bibliography",
    ),
    (re.compile(r"^(?:index|glossary)$", re.IGNORECASE), "index"),
    (
        re.compile(r"^(?:abstract|summary|executive\s+summary)$", re.IGNORECASE),
        "abstract",
    ),
]


def classify_content_type(title: str, node_text: str = "") -> str:
    """Classify content type based on title and optionally node text.

    Returns one of: section, appendix, table, figure, preface, bibliography, toc, index, abstract.
    Default is 'section'.
    """
    title_stripped = title.strip()

    for pattern, content_type in _TITLE_PATTERNS:
        if pattern.search(title_stripped):
            return content_type

    return "section"
