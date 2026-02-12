"""Tests for src/utils/json_utils.py."""

from src.utils.json_utils import extract_json, get_json_content


def test_extract_json_fenced():
    text = '```json\n{"key": "value"}\n```'
    result = extract_json(text)
    assert result == {"key": "value"}


def test_extract_json_bare():
    text = '{"answer": 42}'
    result = extract_json(text)
    assert result == {"answer": 42}


def test_extract_json_with_surrounding_text():
    text = 'Here is the result:\n{"selectedNodeIds": ["0006"]}\nDone.'
    result = extract_json(text)
    assert result == {"selectedNodeIds": ["0006"]}


def test_extract_json_with_python_none():
    text = '```json\n{"value": None}\n```'
    result = extract_json(text)
    assert result == {"value": None}


def test_extract_json_trailing_comma():
    text = '```json\n{"a": 1, "b": 2,}\n```'
    result = extract_json(text)
    assert result == {"a": 1, "b": 2}


def test_extract_json_array():
    text = "```json\n[1, 2, 3]\n```"
    result = extract_json(text)
    assert result == [1, 2, 3]


def test_extract_json_invalid_returns_none():
    result = extract_json("no json here at all")
    assert result is None


def test_extract_json_empty_object():
    """Verify that an actual empty JSON object {} is returned as {}, not None."""
    result = extract_json("{}")
    assert result == {}


def test_get_json_content_strips_fences():
    text = '```json\n{"key": "val"}\n```'
    result = get_json_content(text)
    assert result == '{"key": "val"}'


def test_get_json_content_no_fences():
    text = '{"key": "val"}'
    result = get_json_content(text)
    assert result == '{"key": "val"}'
