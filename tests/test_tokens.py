"""Tests for src/utils/tokens.py."""

from src.utils.tokens import count_tokens, get_encoding


def test_count_tokens_empty():
    assert count_tokens("") == 0
    assert count_tokens("", model="gpt-4o") == 0


def test_count_tokens_nonempty():
    result = count_tokens("Hello, world!")
    assert isinstance(result, int)
    assert result > 0


def test_count_tokens_longer_text():
    short = count_tokens("hi")
    long = count_tokens("This is a longer sentence with many more tokens in it.")
    assert long > short


def test_get_encoding():
    enc = get_encoding("gpt-4o")
    assert enc is not None
    tokens = enc.encode("test")
    assert len(tokens) > 0
