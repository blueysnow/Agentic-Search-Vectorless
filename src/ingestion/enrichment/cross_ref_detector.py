"""Cross-reference detection using regex patterns."""

from __future__ import annotations

import re

# Patterns for cross-references: "see Section X", "refer to Chapter Y", etc.
_CROSS_REF_PATTERNS = [
    re.compile(
        r"(?:see|refer\s+to|as\s+(?:described|discussed|shown)\s+in)\s+(?:Section|Chapter|Appendix|Table|Figure)\s+(\S+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Section|Chapter|Appendix|Table|Figure)\s+(\S+)\s+(?:describes|shows|discusses|contains|provides)",
        re.IGNORECASE,
    ),
]


def detect_cross_references(node_text: str) -> list[dict]:
    """Detect cross-references in node text using regex.

    Returns list of dicts with 'label' and 'type' keys.
    """
    if not node_text:
        return []

    refs: list[dict] = []
    seen: set[str] = set()

    for pattern in _CROSS_REF_PATTERNS:
        for match in pattern.finditer(node_text):
            # Determine type from match context
            context = match.group(0).lower()
            ref_id = match.group(1).rstrip(".,;:)")

            if ref_id in seen:
                continue
            seen.add(ref_id)

            ref_type = "section"
            for t in ("appendix", "table", "figure", "chapter"):
                if t in context:
                    ref_type = t
                    break

            refs.append({"label": ref_id, "type": ref_type})

    return refs
