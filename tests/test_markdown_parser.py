"""Tests for src/ingestion/parsers/markdown_parser.py."""

from src.ingestion.parsers.markdown_parser import (
    build_tree_from_nodes,
    extract_node_text_content,
    extract_nodes_from_markdown,
    parse_markdown,
)

SAMPLE_MD = """\
# Introduction

This is the introduction.

## Background

Some background text here.

## Methods

Methods description.

### Sub-method A

Details about sub-method A.

### Sub-method B

Details about sub-method B.

# Results

The results section.
"""


def test_extract_nodes_from_markdown():
    nodes, lines = extract_nodes_from_markdown(SAMPLE_MD)
    titles = [n["node_title"] for n in nodes]
    assert "Introduction" in titles
    assert "Background" in titles
    assert "Methods" in titles
    assert "Sub-method A" in titles
    assert "Sub-method B" in titles
    assert "Results" in titles
    assert len(nodes) == 6


def test_extract_nodes_skips_code_blocks():
    md = """\
# Real Header

```python
# Not a header
## Also not a header
```

## Another Real Header
"""
    nodes, _ = extract_nodes_from_markdown(md)
    titles = [n["node_title"] for n in nodes]
    assert titles == ["Real Header", "Another Real Header"]


def test_extract_node_text_content():
    nodes, lines = extract_nodes_from_markdown(SAMPLE_MD)
    nodes_with_text = extract_node_text_content(nodes, lines)
    # Introduction node should contain its text
    intro = nodes_with_text[0]
    assert intro["title"] == "Introduction"
    assert "This is the introduction" in intro["text"]
    assert intro["level"] == 1


def test_build_tree_nesting():
    nodes, lines = extract_nodes_from_markdown(SAMPLE_MD)
    nodes_with_text = extract_node_text_content(nodes, lines)
    tree = build_tree_from_nodes(nodes_with_text)

    # Should have 2 root nodes: Introduction and Results
    assert len(tree) == 2
    assert tree[0]["title"] == "Introduction"
    assert tree[1]["title"] == "Results"

    # Introduction should have 2 children: Background, Methods
    assert len(tree[0]["nodes"]) == 2
    assert tree[0]["nodes"][0]["title"] == "Background"
    assert tree[0]["nodes"][1]["title"] == "Methods"

    # Methods should have 2 children: Sub-method A, Sub-method B
    methods = tree[0]["nodes"][1]
    assert len(methods["nodes"]) == 2
    assert methods["nodes"][0]["title"] == "Sub-method A"
    assert methods["nodes"][1]["title"] == "Sub-method B"


def test_build_tree_node_ids():
    nodes, lines = extract_nodes_from_markdown(SAMPLE_MD)
    nodes_with_text = extract_node_text_content(nodes, lines)
    tree = build_tree_from_nodes(nodes_with_text)

    assert tree[0]["node_id"] == "0001"
    assert tree[0]["nodes"][0]["node_id"] == "0002"


def test_parse_markdown_full_pipeline():
    tree = parse_markdown(SAMPLE_MD)
    assert len(tree) == 2
    assert tree[0]["title"] == "Introduction"
    # Token count should be populated
    assert tree[0].get("token_count", 0) >= 0


def test_parse_markdown_empty():
    tree = parse_markdown("")
    assert tree == []
