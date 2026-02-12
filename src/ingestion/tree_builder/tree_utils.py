"""Tree utility functions -- ported from reference utils.py.

All functions operate on dict-based tree nodes with keys:
  title, start_index, end_index, nodes (children), node_id, etc.
"""

from __future__ import annotations

import copy


def write_node_id(data: dict | list, node_id: int = 0) -> int:
    """Assign sequential 4-digit node IDs in pre-order traversal (ref: utils.py:158-168)."""
    if isinstance(data, dict):
        data["node_id"] = str(node_id).zfill(4)
        node_id += 1
        for key in list(data.keys()):
            if "nodes" in key:
                node_id = write_node_id(data[key], node_id)
    elif isinstance(data, list):
        for item in data:
            node_id = write_node_id(item, node_id)
    return node_id


def get_nodes(structure: dict | list) -> list[dict]:
    """Flatten tree excluding children arrays (ref: utils.py:170-183)."""
    if isinstance(structure, dict):
        node = copy.deepcopy(structure)
        node.pop("nodes", None)
        nodes = [node]
        for key in list(structure.keys()):
            if "nodes" in key:
                nodes.extend(get_nodes(structure[key]))
        return nodes
    elif isinstance(structure, list):
        nodes: list[dict] = []
        for item in structure:
            nodes.extend(get_nodes(item))
        return nodes
    return []


def structure_to_list(structure: dict | list) -> list[dict]:
    """Full tree to flat list including the node itself (ref: utils.py:185-196)."""
    if isinstance(structure, dict):
        nodes = [structure]
        if "nodes" in structure:
            nodes.extend(structure_to_list(structure["nodes"]))
        return nodes
    elif isinstance(structure, list):
        nodes: list[dict] = []
        for item in structure:
            nodes.extend(structure_to_list(item))
        return nodes
    return []


def get_leaf_nodes(structure: dict | list) -> list[dict]:
    """Extract leaf nodes (nodes with no children) (ref: utils.py:199-215)."""
    if isinstance(structure, dict):
        if not structure.get("nodes"):
            node = copy.deepcopy(structure)
            node.pop("nodes", None)
            return [node]
        else:
            leaf_nodes: list[dict] = []
            for key in list(structure.keys()):
                if "nodes" in key:
                    leaf_nodes.extend(get_leaf_nodes(structure[key]))
            return leaf_nodes
    elif isinstance(structure, list):
        leaf_nodes = []
        for item in structure:
            leaf_nodes.extend(get_leaf_nodes(item))
        return leaf_nodes
    return []


def is_leaf_node(data: dict | list, node_id: str) -> bool:
    """Check if a node with given node_id is a leaf (ref: utils.py:217-241)."""

    def find_node(data: dict | list, node_id: str) -> dict | None:
        if isinstance(data, dict):
            if data.get("node_id") == node_id:
                return data
            for key in data.keys():
                if "nodes" in key:
                    result = find_node(data[key], node_id)
                    if result:
                        return result
        elif isinstance(data, list):
            for item in data:
                result = find_node(item, node_id)
                if result:
                    return result
        return None

    node = find_node(data, node_id)
    if node and not node.get("nodes"):
        return True
    return False


def list_to_tree(data: list[dict]) -> list[dict]:
    """Convert flat list with structure codes to nested tree (ref: utils.py:350-396)."""

    def get_parent_structure(structure: str | None) -> str | None:
        if not structure:
            return None
        parts = str(structure).split(".")
        return ".".join(parts[:-1]) if len(parts) > 1 else None

    nodes: dict[str, dict] = {}
    root_nodes: list[dict] = []

    for item in data:
        structure = item.get("structure")
        node: dict = {
            "title": item.get("title"),
            "start_index": item.get("start_index"),
            "end_index": item.get("end_index"),
            "nodes": [],
        }
        nodes[structure] = node
        parent_structure = get_parent_structure(structure)

        if parent_structure and parent_structure in nodes:
            nodes[parent_structure]["nodes"].append(node)
        else:
            root_nodes.append(node)

    def clean_node(node: dict) -> dict:
        if not node["nodes"]:
            del node["nodes"]
        else:
            for child in node["nodes"]:
                clean_node(child)
        return node

    return [clean_node(node) for node in root_nodes]


def post_processing(structure: list[dict], end_physical_index: int) -> list[dict]:
    """Convert physical_index to start/end pages (ref: utils.py:460-479)."""
    for i, item in enumerate(structure):
        item["start_index"] = item.get("physical_index")
        if i < len(structure) - 1:
            if structure[i + 1].get("appear_start") == "yes":
                item["end_index"] = structure[i + 1]["physical_index"] - 1
            else:
                item["end_index"] = structure[i + 1]["physical_index"]
        else:
            item["end_index"] = end_physical_index

    tree = list_to_tree(structure)
    if tree:
        return tree
    else:
        for node in structure:
            node.pop("appear_start", None)
            node.pop("physical_index", None)
        return structure


def add_preface_if_needed(data: list[dict]) -> list[dict]:
    """Add preface node if doc starts after page 1 (ref: utils.py:398-409)."""
    if not isinstance(data, list) or not data:
        return data
    if data[0].get("physical_index") is not None and data[0]["physical_index"] > 1:
        preface_node = {
            "structure": "0",
            "title": "Preface",
            "physical_index": 1,
        }
        data.insert(0, preface_node)
    return data


def add_node_text(node: dict | list, page_list: list[tuple]) -> None:
    """Attach page text to nodes (ref: utils.py:579-589)."""
    if isinstance(node, dict):
        start_page = node.get("start_index")
        end_page = node.get("end_index")
        if start_page is not None and end_page is not None:
            text = ""
            for page_num in range(start_page - 1, end_page):
                if 0 <= page_num < len(page_list):
                    text += page_list[page_num][0]
            node["text"] = text
        if "nodes" in node:
            add_node_text(node["nodes"], page_list)
    elif isinstance(node, list):
        for item in node:
            add_node_text(item, page_list)


def convert_physical_index_to_int(data: list[dict] | str) -> list[dict] | int | None:
    """Parse '<physical_index_N>' strings to int (ref: utils.py:545-565)."""
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "physical_index" in item:
                val = item["physical_index"]
                if isinstance(val, str):
                    try:
                        if val.startswith("<physical_index_"):
                            item["physical_index"] = int(
                                val.split("_")[-1].rstrip(">").strip()
                            )
                        elif val.startswith("physical_index_"):
                            item["physical_index"] = int(val.split("_")[-1].strip())
                    except ValueError:
                        item["physical_index"] = None
        return data
    elif isinstance(data, str):
        try:
            if data.startswith("<physical_index_"):
                return int(data.split("_")[-1].rstrip(">").strip())
            elif data.startswith("physical_index_"):
                return int(data.split("_")[-1].strip())
        except ValueError:
            return None
        return None
    return data
