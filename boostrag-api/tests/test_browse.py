import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient


def _write_legacy(dirpath, name, *, brand="B", category="Intake", product="P",
                   url="https://ecstuning.com/x", price="$1.00", body="Summary:\nSome body text."):
    dirpath.mkdir(parents=True, exist_ok=True)
    content = (
        f"Brand: {brand}\n"
        f"Category: {category}\n"
        f"Product: {product}\n"
        f"Vehicle: BMW M340i G20\n"
        f"Source Type: Product Page\n"
        f"URL: {url}\n"
        f"Price: {price}\n"
        f"\n"
        f"{body}"
    )
    (dirpath / f"{name}.txt").write_text(content, encoding="utf-8")


def _write_ingested(dirpath, name, *, brand="B", category="Intake", source_title="P",
                     source_url="https://example.com/x", trust_tier="1", price="$1.00",
                     body="--- Extracted Page Text ---\n\nSome body text."):
    dirpath.mkdir(parents=True, exist_ok=True)
    content = (
        f"Source Title: {source_title}\n"
        f"Source URL: {source_url}\n"
        f"Source Domain: example.com\n"
        f"Brand: {brand}\n"
        f"Category: {category}\n"
        f"Vehicle: BMW M340i G20\n"
        f"Price: {price}\n"
        f"Source Type: product_page\n"
        f"Trust Tier: {trust_tier}\n"
        f"Review Status: auto_approved\n"
        f"\n"
        f"{body}"
    )
    (dirpath / f"{name}.txt").write_text(content, encoding="utf-8")


def test_browse_legacy_file_appears_with_domain_derived_trust_tier(tmp_path, monkeypatch):
    import browse
    cleaned = tmp_path / "cleaned"
    monkeypatch.setattr(browse, "CLEANED_DIR", cleaned)
    _write_legacy(
        cleaned, "a",
        category="Intake", product="Legacy Intake",
        url="https://www.ecstuning.com/some-part/",
    )

    result = browse.browse_category("intake-exhaust")
    assert result["count"] == 1
    item = result["items"][0]
    assert item["product"] == "Legacy Intake"
    assert item["url"] == "https://www.ecstuning.com/some-part/"
    assert item["trust_tier"] == "Tier 1"


def test_browse_ingested_file_uses_source_title_and_header_trust_tier(tmp_path, monkeypatch):
    import browse
    cleaned = tmp_path / "cleaned"
    monkeypatch.setattr(browse, "CLEANED_DIR", cleaned)
    _write_ingested(
        cleaned, "b",
        category="Downpipe", source_title="Ingested Downpipe",
        source_url="https://unknown-vendor.example/part", trust_tier="3",
    )

    result = browse.browse_category("intake-exhaust")
    assert result["count"] == 1
    item = result["items"][0]
    assert item["product"] == "Ingested Downpipe"
    assert item["url"] == "https://unknown-vendor.example/part"
    assert item["trust_tier"] == "3"


def test_browse_category_filters_across_slugs(tmp_path, monkeypatch):
    import browse
    cleaned = tmp_path / "cleaned"
    monkeypatch.setattr(browse, "CLEANED_DIR", cleaned)
    _write_legacy(cleaned, "a", category="Intake", product="Intake A")
    _write_legacy(cleaned, "b", category="Downpipe", product="DP B")
    _write_legacy(cleaned, "c", category="Charge Pipe", product="CP C")
    _write_legacy(cleaned, "d", category="Cooling", product="Cool D")

    result = browse.browse_category("intake-exhaust")
    names = [i["product"] for i in result["items"]]
    assert result["count"] == 3
    assert "Intake A" in names and "DP B" in names and "CP C" in names
    assert "Cool D" not in names

    cooling_result = browse.browse_category("cooling")
    cooling_names = [i["product"] for i in cooling_result["items"]]
    assert cooling_result["count"] == 1
    assert "Cool D" in cooling_names


def test_browse_overview_returns_all(tmp_path, monkeypatch):
    import browse
    cleaned = tmp_path / "cleaned"
    monkeypatch.setattr(browse, "CLEANED_DIR", cleaned)
    _write_legacy(cleaned, "a", category="Intake")
    _write_legacy(cleaned, "b", category="Suspension")
    result = browse.browse_category("overview")
    assert result["count"] == 2


def test_browse_unknown_slug_returns_none_and_404(tmp_path, monkeypatch):
    import browse
    cleaned = tmp_path / "cleaned"
    monkeypatch.setattr(browse, "CLEANED_DIR", cleaned)
    assert browse.browse_category("boats") is None

    with patch("main.ensure_chroma_collection"):
        import importlib, main
        importlib.reload(main)
        client = TestClient(main.app)
    resp = client.get("/browse", params={"category": "boats"})
    assert resp.status_code == 404


def test_browse_route_does_not_consume_daily_ask_cap(tmp_path, monkeypatch):
    import browse, provenance
    cleaned = tmp_path / "cleaned"
    monkeypatch.setattr(browse, "CLEANED_DIR", cleaned)
    monkeypatch.setattr(provenance, "ASK_COUNTER_PATH", tmp_path / "ask.json")
    _write_legacy(cleaned, "a", category="Turbo Inlet")
    with patch("main.ensure_chroma_collection"):
        import importlib, main
        importlib.reload(main)
        client = TestClient(main.app)
    resp = client.get("/browse", params={"category": "engine"})
    assert resp.status_code == 200
    assert provenance.asks_today() == 0
