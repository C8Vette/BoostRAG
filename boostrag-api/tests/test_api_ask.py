import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from rag_types import AnswerResult


def _client():
    with patch("main.ensure_chroma_collection"):
        import main
        return TestClient(main.app)


def test_ask_returns_origin_and_sources():
    result = AnswerResult(
        answer="web answer", origin="web",
        sources=[{"product": "VRSF", "url": "u", "origin": "web",
                  "trust_tier": "strong_candidate", "price": None, "text_preview": "..."}],
        confidence={"sufficient": False, "nearest_distance": None},
    )
    with patch("main.answer_question", return_value=result):
        resp = _client().post("/ask", json={"query": "downpipe?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["origin"] == "web"
    assert body["sources"][0]["trust_tier"] == "strong_candidate"


def test_ask_rejects_empty_query():
    resp = _client().post("/ask", json={"query": "   "})
    assert resp.status_code == 400
