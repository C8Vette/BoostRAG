import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from rag_types import AnswerResult


def test_over_cap_returns_friendly_notice(monkeypatch, tmp_path):
    monkeypatch.setenv("DAILY_ASK_CAP", "1")
    monkeypatch.setenv("RATE_LIMIT", "100/minute")
    import provenance
    monkeypatch.setattr(provenance, "ASK_COUNTER_PATH", tmp_path / "ask.json")
    with patch("main.ensure_chroma_collection"):
        import importlib, main; importlib.reload(main)
        client = TestClient(main.app)
    result = AnswerResult(answer="a", origin="corpus", sources=[], confidence={})
    with patch("main.answer_question", return_value=result):
        r1 = client.post("/ask", json={"query": "q"})
        r2 = client.post("/ask", json={"query": "q"})
    assert r1.status_code == 200 and r1.json()["origin"] == "corpus"
    assert r2.status_code == 200 and r2.json()["origin"] == "none"
    assert "busy day" in r2.json()["answer"].lower()
