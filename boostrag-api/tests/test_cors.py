import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient


def _client():
    with patch("main.ensure_chroma_collection"):
        import importlib, main; importlib.reload(main)
        return TestClient(main.app)


def test_allowed_origin_is_echoed(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://boostrag.vercel.app")
    resp = _client().get("/", headers={"Origin": "https://boostrag.vercel.app"})
    assert resp.headers.get("access-control-allow-origin") == "https://boostrag.vercel.app"


def test_default_allows_localhost(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    resp = _client().get("/", headers={"Origin": "http://localhost:5173"})
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
