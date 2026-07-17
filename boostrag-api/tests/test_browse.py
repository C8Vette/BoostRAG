import json
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient


def _write_meta(dirpath, name, **fields):
    dirpath.mkdir(parents=True, exist_ok=True)
    base = {"product": "P", "brand": "B", "price": "$1.00", "url": "https://x/",
            "category": "Intake", "route": "cleaned", "description": "d",
            "title": "T"}
    base.update(fields)
    (dirpath / f"{name}.json").write_text(json.dumps(base), encoding="utf-8")


def test_browse_category_filters_and_shapes(tmp_path, monkeypatch):
    import browse
    monkeypatch.setattr(browse, "METADATA_DIR", tmp_path / "metadata")
    meta = tmp_path / "metadata"
    _write_meta(meta, "a", category="Intake", product="Intake A", trust_tier=1)
    _write_meta(meta, "b", category="Downpipe", product="DP B", trust_tier=1)
    _write_meta(meta, "c", category="Cooling", product="Cool C", trust_tier=1)
    _write_meta(meta, "q", category="Intake", product="Quarantined", route="quarantine")

    result = browse.browse_category("intake-exhaust")
    names = [i["product"] for i in result["items"]]
    assert result["count"] == 2
    assert "Intake A" in names and "DP B" in names
    assert "Cool C" not in names            # wrong category
    assert "Quarantined" not in names       # only cleaned-routed items


def test_browse_overview_returns_all_cleaned(tmp_path, monkeypatch):
    import browse
    monkeypatch.setattr(browse, "METADATA_DIR", tmp_path / "metadata")
    meta = tmp_path / "metadata"
    _write_meta(meta, "a", category="Intake")
    _write_meta(meta, "b", category="Suspension")
    result = browse.browse_category("overview")
    assert result["count"] == 2


def test_browse_unknown_slug_returns_none_and_404(tmp_path, monkeypatch):
    import browse
    monkeypatch.setattr(browse, "METADATA_DIR", tmp_path / "metadata")
    assert browse.browse_category("boats") is None

    with patch("main.ensure_chroma_collection"):
        import importlib, main
        importlib.reload(main)
        client = TestClient(main.app)
    resp = client.get("/browse", params={"category": "boats"})
    assert resp.status_code == 404


def test_browse_route_does_not_consume_daily_ask_cap(tmp_path, monkeypatch):
    import browse, provenance
    monkeypatch.setattr(browse, "METADATA_DIR", tmp_path / "metadata")
    monkeypatch.setattr(provenance, "ASK_COUNTER_PATH", tmp_path / "ask.json")
    _write_meta(tmp_path / "metadata", "a", category="Intake")
    with patch("main.ensure_chroma_collection"):
        import importlib, main
        importlib.reload(main)
        client = TestClient(main.app)
    resp = client.get("/browse", params={"category": "engine"})
    assert resp.status_code == 200
    assert provenance.asks_today() == 0
