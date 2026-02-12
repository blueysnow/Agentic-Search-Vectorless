"""Tests for src/ingestion/tree_builder/tree_utils.py."""

import pytest

from src.ingestion.tree_builder.tree_utils import (
    add_node_text,
    add_preface_if_needed,
    convert_physical_index_to_int,
    get_leaf_nodes,
    get_nodes,
    is_leaf_node,
    list_to_tree,
    post_processing,
    structure_to_list,
    write_node_id,
)


# --- Fixtures ---


@pytest.fixture
def simple_tree():
    return {
        "title": "Root",
        "nodes": [
            {"title": "Child A", "nodes": []},
            {
                "title": "Child B",
                "nodes": [
                    {"title": "Grandchild B1", "nodes": []},
                ],
            },
        ],
    }


@pytest.fixture
def flat_list():
    return [
        {"structure": "1", "title": "Intro", "start_index": 1, "end_index": 3},
        {"structure": "2", "title": "Body", "start_index": 4, "end_index": 8},
        {"structure": "2.1", "title": "Part A", "start_index": 4, "end_index": 6},
        {"structure": "2.2", "title": "Part B", "start_index": 7, "end_index": 8},
        {"structure": "3", "title": "Conclusion", "start_index": 9, "end_index": 10},
    ]


# --- write_node_id ---


def test_write_node_id_assigns_sequential_ids(simple_tree):
    write_node_id(simple_tree)
    assert simple_tree["node_id"] == "0000"
    assert simple_tree["nodes"][0]["node_id"] == "0001"
    assert simple_tree["nodes"][1]["node_id"] == "0002"
    assert simple_tree["nodes"][1]["nodes"][0]["node_id"] == "0003"


def test_write_node_id_returns_next_counter(simple_tree):
    result = write_node_id(simple_tree)
    assert result == 4


def test_write_node_id_list_input():
    data = [{"title": "A", "nodes": []}, {"title": "B", "nodes": []}]
    result = write_node_id(data)
    assert data[0]["node_id"] == "0000"
    assert data[1]["node_id"] == "0001"
    assert result == 2


def test_write_node_id_custom_start():
    data = {"title": "X", "nodes": []}
    result = write_node_id(data, node_id=10)
    assert data["node_id"] == "0010"
    assert result == 11


# --- get_nodes ---


def test_get_nodes_flattens_without_children(simple_tree):
    nodes = get_nodes(simple_tree)
    assert len(nodes) == 4
    titles = [n["title"] for n in nodes]
    assert "Root" in titles
    assert "Child A" in titles
    assert "Grandchild B1" in titles
    # No node should have 'nodes' key
    for n in nodes:
        assert "nodes" not in n


def test_get_nodes_with_list():
    data = [{"title": "A", "nodes": []}, {"title": "B", "nodes": []}]
    nodes = get_nodes(data)
    assert len(nodes) == 2


# --- structure_to_list ---


def test_structure_to_list_includes_node_itself(simple_tree):
    result = structure_to_list(simple_tree)
    # Root + Child A + Child B + Grandchild B1
    assert len(result) == 4
    assert result[0]["title"] == "Root"


def test_structure_to_list_from_list():
    data = [{"title": "A"}, {"title": "B", "nodes": [{"title": "C"}]}]
    result = structure_to_list(data)
    assert len(result) == 3


# --- get_leaf_nodes ---


def test_get_leaf_nodes(simple_tree):
    leaves = get_leaf_nodes(simple_tree)
    titles = [leaf["title"] for leaf in leaves]
    assert "Child A" in titles
    assert "Grandchild B1" in titles
    assert "Root" not in titles
    assert "Child B" not in titles


def test_get_leaf_nodes_single_node():
    data = {"title": "Only", "nodes": []}
    leaves = get_leaf_nodes(data)
    assert len(leaves) == 1
    assert leaves[0]["title"] == "Only"


# --- is_leaf_node ---


def test_is_leaf_node_true(simple_tree):
    write_node_id(simple_tree)
    assert is_leaf_node(simple_tree, "0001") is True  # Child A has no children


def test_is_leaf_node_false(simple_tree):
    write_node_id(simple_tree)
    assert is_leaf_node(simple_tree, "0002") is False  # Child B has Grandchild


def test_is_leaf_node_not_found(simple_tree):
    write_node_id(simple_tree)
    assert is_leaf_node(simple_tree, "9999") is False


# --- list_to_tree ---


def test_list_to_tree_basic(flat_list):
    tree = list_to_tree(flat_list)
    assert len(tree) == 3  # Intro, Body, Conclusion
    body = tree[1]
    assert body["title"] == "Body"
    assert len(body["nodes"]) == 2
    assert body["nodes"][0]["title"] == "Part A"


def test_list_to_tree_cleans_empty_nodes():
    data = [{"structure": "1", "title": "Alone", "start_index": 1, "end_index": 5}]
    tree = list_to_tree(data)
    assert len(tree) == 1
    assert "nodes" not in tree[0]


# --- post_processing ---


def test_post_processing_converts_indices():
    data = [
        {"structure": "1", "title": "A", "physical_index": 1, "appear_start": "yes"},
        {"structure": "2", "title": "B", "physical_index": 5, "appear_start": "no"},
    ]
    result = post_processing(data, 10)
    # Should build a tree
    assert isinstance(result, list)
    assert len(result) >= 1


def test_post_processing_single_item():
    data = [
        {"structure": "1", "title": "Solo", "physical_index": 1, "appear_start": "yes"}
    ]
    result = post_processing(data, 10)
    assert isinstance(result, list)


# --- add_preface_if_needed ---


def test_add_preface_when_doc_starts_after_page_1():
    data = [{"structure": "1", "title": "Intro", "physical_index": 3}]
    result = add_preface_if_needed(data)
    assert result[0]["title"] == "Preface"
    assert result[0]["physical_index"] == 1


def test_no_preface_when_starts_at_page_1():
    data = [{"structure": "1", "title": "Intro", "physical_index": 1}]
    result = add_preface_if_needed(data)
    assert result[0]["title"] == "Intro"


def test_add_preface_empty_list():
    result = add_preface_if_needed([])
    assert result == []


# --- add_node_text ---


def test_add_node_text():
    page_list = [("Page1 ", 10), ("Page2 ", 10), ("Page3 ", 10)]
    node = {"title": "Test", "start_index": 1, "end_index": 2}
    add_node_text(node, page_list)
    assert node["text"] == "Page1 Page2 "


def test_add_node_text_recursive():
    page_list = [("A ", 1), ("B ", 1), ("C ", 1), ("D ", 1)]
    tree = {
        "title": "Root",
        "start_index": 1,
        "end_index": 4,
        "nodes": [
            {"title": "Child", "start_index": 3, "end_index": 4},
        ],
    }
    add_node_text(tree, page_list)
    assert tree["text"] == "A B C D "
    assert tree["nodes"][0]["text"] == "C D "


# --- convert_physical_index_to_int ---


def test_convert_physical_index_angle_brackets():
    data = [{"title": "A", "physical_index": "<physical_index_5>"}]
    result = convert_physical_index_to_int(data)
    assert result[0]["physical_index"] == 5


def test_convert_physical_index_no_brackets():
    data = [{"title": "A", "physical_index": "physical_index_12"}]
    result = convert_physical_index_to_int(data)
    assert result[0]["physical_index"] == 12


def test_convert_physical_index_already_int():
    data = [{"title": "A", "physical_index": 7}]
    result = convert_physical_index_to_int(data)
    assert result[0]["physical_index"] == 7


def test_convert_physical_index_string():
    result = convert_physical_index_to_int("<physical_index_42>")
    assert result == 42


def test_convert_physical_index_invalid_string():
    result = convert_physical_index_to_int("not_valid")
    assert result is None
