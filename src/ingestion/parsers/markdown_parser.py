"""Markdown parsing -- adapted from reference page_index_md.py.

Extracts headers, builds hierarchy, computes text per node.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.utils.tokens import count_tokens


@dataclass
class MarkdownNode:
    """A section extracted from a Markdown document."""

    title: str
    level: int  # 1-6
    line_number: int
    text: str = ""
    token_count: int = 0
    children: list["MarkdownNode"] = field(default_factory=list)


def extract_nodes_from_markdown(markdown_content: str) -> tuple[list[dict], list[str]]:
    """Extract header nodes from markdown content.

    Adapted from reference extract_nodes_from_markdown().

    Returns:
        (node_list, lines) where each node has 'node_title' and 'line_num'.
    """
    header_pattern = r"^(#{1,6})\s+(.+)$"
    code_block_pattern = r"^```"
    node_list: list[dict] = []
    lines = markdown_content.split("\n")
    in_code_block = False

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()

        if re.match(code_block_pattern, stripped):
            in_code_block = not in_code_block
            continue

        if not stripped:
            continue

        if not in_code_block:
            match = re.match(header_pattern, stripped)
            if match:
                title = match.group(2).strip()
                node_list.append({"node_title": title, "line_num": line_num})

    return node_list, lines


def extract_node_text_content(
    node_list: list[dict], markdown_lines: list[str]
) -> list[dict]:
    """Attach text content to each extracted header node.

    Adapted from reference extract_node_text_content().
    """
    all_nodes: list[dict] = []
    for node in node_list:
        line_content = markdown_lines[node["line_num"] - 1]
        header_match = re.match(r"^(#{1,6})", line_content)
        if header_match is None:
            continue
        all_nodes.append(
            {
                "title": node["node_title"],
                "line_num": node["line_num"],
                "level": len(header_match.group(1)),
            }
        )

    for i, node in enumerate(all_nodes):
        start_line = node["line_num"] - 1
        end_line = (
            all_nodes[i + 1]["line_num"] - 1
            if i + 1 < len(all_nodes)
            else len(markdown_lines)
        )
        node["text"] = "\n".join(markdown_lines[start_line:end_line]).strip()

    return all_nodes


def build_tree_from_nodes(node_list: list[dict]) -> list[dict]:
    """Build a nested tree from the flat node list.

    Adapted from reference build_tree_from_nodes().
    """
    if not node_list:
        return []

    stack: list[tuple[dict, int]] = []
    root_nodes: list[dict] = []
    node_counter = 1

    for node in node_list:
        level = node["level"]
        tree_node: dict = {
            "title": node["title"],
            "node_id": str(node_counter).zfill(4),
            "text": node.get("text", ""),
            "line_num": node["line_num"],
            "level": level,
            "nodes": [],
        }
        node_counter += 1

        while stack and stack[-1][1] >= level:
            stack.pop()

        if not stack:
            root_nodes.append(tree_node)
        else:
            parent_node, _ = stack[-1]
            parent_node["nodes"].append(tree_node)

        stack.append((tree_node, level))

    return root_nodes


def parse_markdown(content: str, *, model: str = "gpt-4o") -> list[dict]:
    """Full markdown parsing pipeline: extract -> attach text -> build tree.

    Returns a nested tree of dicts with keys:
    title, node_id, text, line_num, level, nodes (children).
    """
    node_list, lines = extract_nodes_from_markdown(content)
    nodes_with_content = extract_node_text_content(node_list, lines)

    # Attach token counts
    for node in nodes_with_content:
        node["token_count"] = count_tokens(node.get("text", ""), model=model)

    return build_tree_from_nodes(nodes_with_content)
