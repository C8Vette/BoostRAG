import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from rag_types import AnswerResult


def _client(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT", "2/minute")
    with patch("main.ensure_chroma_collection"):
        # reloading main builds a fresh Limiter with empty in-memory state,
        # isolating rate-limit counts between tests (no shared limiter bleed)
        import importlib, main; importlib.reload(main)
        client = TestClient(main.app)
        return main, client


def test_third_request_in_window_is_rate_limited(monkeypatch):
    main, client = _client(monkeypatch)
    result = AnswerResult(answer="a", origin="corpus", sources=[], confidence={})
    with patch("main.answer_question", return_value=result):
        r1 = client.post("/ask", json={"query": "q"})
        r2 = client.post("/ask", json={"query": "q"})
        r3 = client.post("/ask", json={"query": "q"})
    assert r1.status_code == 200 and r2.status_code == 200
    assert r3.status_code == 429
    assert "slow down" in r3.json()["detail"].lower()
