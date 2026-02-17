"""Tests for src/ingestion/math_extractor.py."""

from src.ingestion.math_extractor import detect_math_regions, has_math


# --- has_math tests ---


def test_has_math_inline():
    assert has_math("The formula is $x^2 + y^2 = r^2$ in polar form.") is True


def test_has_math_block():
    assert has_math("$$\\frac{d}{dx}\\sin(x) = \\cos(x)$$") is True


def test_has_math_begin_equation():
    assert has_math("\\begin{equation} E = mc^2 \\end{equation}") is True


def test_has_math_begin_align():
    assert has_math("\\begin{align*} a &= b \\\\ c &= d \\end{align*}") is True


def test_has_math_false_on_plain_text():
    assert has_math("This is plain Korean text without any math.") is False


def test_has_math_false_on_empty():
    assert has_math("") is False


def test_has_math_false_on_raw_pdf_garbled():
    assert has_math("f(x) = \ufffd\ufffd + \ufffd\ufffd") is False


def test_has_math_false_on_currency():
    # Single dollar signs without math content pattern
    assert has_math("The price is 50 dollars.") is False


def test_has_math_inline_does_not_match_block():
    # $$ should NOT be detected as two inline $ matches
    assert has_math("$$x^2$$") is True  # detected as block math
    result = detect_math_regions("$$x^2$$")
    assert result["block_count"] == 1
    assert result["inline_count"] == 0


def test_has_math_gather_env():
    """\\begin{gather} environment is detected."""
    assert has_math("\\begin{gather} a = b \\\\ c = d \\end{gather}") is True


def test_has_math_multline_env():
    """\\begin{multline} environment is detected."""
    assert has_math("\\begin{multline} a + b + c \\\\ = d \\end{multline}") is True


def test_has_math_starred_align():
    """\\begin{align*} (starred variant) is detected."""
    assert has_math("\\begin{align*} x = y \\end{align*}") is True


# --- detect_math_regions tests ---


def test_detect_math_regions_mixed():
    text = "Solve $a + b = c$ and $x^2 = 4$. Also $$\\int_0^1 f(x) dx = 1$$."
    result = detect_math_regions(text)
    assert result["has_math"] is True
    assert result["inline_count"] == 2
    assert result["block_count"] == 1
    assert result["equation_env_count"] == 0


def test_detect_math_regions_equation_env():
    text = "\\begin{equation} a = b \\end{equation} and \\begin{align} c = d \\end{align}"
    result = detect_math_regions(text)
    assert result["equation_env_count"] == 2


def test_detect_math_regions_no_math():
    result = detect_math_regions("Plain text with no math at all.")
    assert result["has_math"] is False
    assert result["inline_count"] == 0
    assert result["block_count"] == 0
    assert result["equation_env_count"] == 0


def test_detect_math_regions_empty():
    result = detect_math_regions("")
    assert result["has_math"] is False
    assert result["inline_count"] == 0
    assert result["block_count"] == 0
    assert result["equation_env_count"] == 0


def test_detect_math_regions_block_not_counted_as_inline():
    """Block math $$ should not inflate inline_count."""
    text = "$$a + b = c$$"
    result = detect_math_regions(text)
    assert result["block_count"] == 1
    assert result["inline_count"] == 0
    assert result["has_math"] is True


def test_detect_math_regions_multiple_blocks():
    text = "$$a$$, $$b$$, and $c$ inline."
    result = detect_math_regions(text)
    assert result["block_count"] == 2
    assert result["inline_count"] == 1
