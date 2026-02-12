"""Tests for Pydantic data models in src/models/."""

from src.models.document import Document
from src.models.node import CrossReference, Node
from src.models.page import Page
from src.models.retrieval import ReasonerResponse, RetrievalCandidate
from src.models.session import RetrievalSession, Turn


def test_document_creation():
    doc = Document(documentId="doc_test", name="test.pdf", type="pdf")
    assert doc.document_id == "doc_test"
    assert doc.name == "test.pdf"
    assert doc.type == "pdf"
    assert doc.ingestion.status == "pending"


def test_document_to_mongo():
    doc = Document(documentId="doc1", name="test.pdf", type="pdf", domain="finance")
    d = doc.to_mongo()
    assert d["documentId"] == "doc1"
    assert d["domain"] == "finance"
    assert "ingestion" in d
    assert d["ingestion"]["status"] == "pending"


def test_node_hybrid_tree():
    node = Node(
        nodeId="0006",
        documentId="doc1",
        parentNodeId="0003",
        materializedPath="/0001/0003/0006",
        childNodeIds=["0007", "0008"],
        depth=2,
        siblingOrder=3,
        title="Financial Stability",
        isLeaf=False,
    )
    assert node.node_id == "0006"
    assert node.parent_node_id == "0003"
    assert node.materialized_path == "/0001/0003/0006"
    assert node.child_node_ids == ["0007", "0008"]
    assert node.depth == 2
    assert node.sibling_order == 3


def test_node_cross_references():
    node = Node(
        nodeId="0006",
        documentId="doc1",
        crossReferences=[
            CrossReference(
                targetNodeId="0020", label="See Appendix G", type="appendix"
            ),
        ],
    )
    d = node.to_mongo()
    assert len(d["crossReferences"]) == 1
    assert d["crossReferences"][0]["targetNodeId"] == "0020"


def test_page_creation():
    page = Page(
        documentId="doc1",
        pageNumber=21,
        nodeId="0006",
        content="some text",
        tokenCount=100,
    )
    assert page.page_number == 21
    d = page.to_mongo()
    assert d["pageNumber"] == 21
    assert d["documentId"] == "doc1"


def test_retrieval_session():
    session = RetrievalSession(sessionId="sess1", documentId="doc1")
    assert session.session_id == "sess1"
    assert session.turns == []


def test_turn():
    turn = Turn(turnNumber=1, query="test query", answer="test answer", model="gpt-4o")
    assert turn.turn_number == 1


def test_retrieval_candidate():
    c = RetrievalCandidate(
        nodeId="0006", atlasScore=0.8, treeScore=1.0, finalScore=0.94
    )
    assert c.node_id == "0006"
    assert c.final_score == 0.94


def test_reasoner_response_sufficient():
    r = ReasonerResponse(answer="The answer is 42", confidence=0.95, sufficient=True)
    assert r.sufficient is True
    assert r.next_action is None


def test_reasoner_response_insufficient():
    r = ReasonerResponse(
        confidence=0.3,
        sufficient=False,
        nextAction={
            "type": "follow_reference",
            "targetNodeId": "0020",
            "reasoning": "Need appendix",
        },
    )
    assert r.sufficient is False
    assert r.next_action is not None
    assert r.next_action.target_node_id == "0020"
