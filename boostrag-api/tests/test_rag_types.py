import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_retrieved_context_defaults():
    from rag_types import RetrievedContext
    c = RetrievedContext(text="t", metadata={"url": "u"}, origin="corpus")
    assert c.trust_score is None and c.distance is None and c.url is None


def test_answer_result_shape():
    from rag_types import AnswerResult
    r = AnswerResult(answer="a", origin="web", sources=[], confidence={"sufficient": False})
    assert r.origin == "web" and r.sources == []
