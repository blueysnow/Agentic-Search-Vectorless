"""Token counting utilities -- adapted from reference pageindex/utils.py count_tokens()."""

from __future__ import annotations

from functools import lru_cache

import tiktoken

# Default model for token counting
_DEFAULT_MODEL = "gpt-4o"


@lru_cache(maxsize=4)
def get_encoding(model: str = _DEFAULT_MODEL) -> tiktoken.Encoding:
    """Return a cached tiktoken Encoding for a model."""
    return tiktoken.encoding_for_model(model)


def count_tokens(text: str, model: str = _DEFAULT_MODEL) -> int:
    """Count the number of tokens in *text* for the given model.

    Uses tiktoken natively (same as reference code).
    """
    if not text:
        return 0
    enc = get_encoding(model)
    return len(enc.encode(text))
