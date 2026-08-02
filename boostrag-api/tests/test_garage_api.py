import sys, time
from pathlib import Path
from unittest.mock import patch
import jwt
sys.path.insert(0, str(Path(__file__).parent.parent))
from fastapi.testclient import TestClient
from rag_types import AnswerResult

SECRET = "test-secret"


def _tok(sub="u1"):
    return jwt.encode({"sub": sub, "aud": "authenticated", "exp": int(time.time()) + 3600}, SECRET, algorithm="HS256")


def _client(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    monkeypatch.setenv("RATE_LIMIT", "100/minute")
    with patch("main.ensure_chroma_collection"):
        import importlib, main
        importlib.reload(main)
        return main, TestClient(main.app)


def test_garage_requires_auth(monkeypatch):
    main, c = _client(monkeypatch)
    assert c.get("/garage").status_code == 401


def test_garage_get_returns_store(monkeypatch):
    main, c = _client(monkeypatch)
    with patch.object(main.garage_store, "get_garage", return_value={"garage": {"model": "M340i"}, "mods": []}) as g:
        r = c.get("/garage", headers={"Authorization": f"Bearer {_tok()}"})
    assert r.status_code == 200 and r.json()["garage"]["model"] == "M340i"
    assert g.call_args.args[0] == "u1"   # scoped to jwt uid


def test_ask_injects_context_when_logged_in(monkeypatch):
    main, c = _client(monkeypatch)
    res = AnswerResult(answer="a", origin="corpus", sources=[], confidence={})
    with patch.object(main.garage_store, "get_garage",
                      return_value={"garage": {"year": 2021, "model": "M340i", "context_on": True},
                                    "mods": [{"category": "Engine", "name": "BM3"}]}), \
         patch("main.answer_question", return_value=res) as aq:
        c.post("/ask", json={"query": "dp?"}, headers={"Authorization": f"Bearer {_tok()}"})
    assert "BM3" in (aq.call_args.kwargs.get("user_context") or "")


def test_ask_degrades_when_store_fails(monkeypatch):
    main, c = _client(monkeypatch)
    res = AnswerResult(answer="a", origin="corpus", sources=[], confidence={})
    with patch.object(main.garage_store, "get_garage", side_effect=main.garage_store.GarageUnavailable("down")), \
         patch("main.answer_question", return_value=res) as aq:
        r = c.post("/ask", json={"query": "dp?"}, headers={"Authorization": f"Bearer {_tok()}"})
    assert r.status_code == 200                                  # answer still delivered
    assert aq.call_args.kwargs.get("user_context") in (None, "")


def test_ask_anonymous_unchanged(monkeypatch):
    main, c = _client(monkeypatch)
    res = AnswerResult(answer="a", origin="corpus", sources=[], confidence={})
    with patch("main.answer_question", return_value=res) as aq:
        c.post("/ask", json={"query": "dp?"})
    assert aq.call_args.kwargs.get("user_context") in (None, "")
