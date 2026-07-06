import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_provenance_fields_written_to_metadata(tmp_path, monkeypatch):
    import ingest_urls
    # redirect all output dirs into tmp_path
    monkeypatch.setattr(ingest_urls, "CLEANED_DIR", tmp_path / "cleaned")
    monkeypatch.setattr(ingest_urls, "LIMITED_DIR", tmp_path / "limited")
    monkeypatch.setattr(ingest_urls, "QUARANTINE_DIR", tmp_path / "quarantine")
    monkeypatch.setattr(ingest_urls, "METADATA_DIR", tmp_path / "metadata")

    body = "BMW M340i B58 VRSF catted downpipe. " * 30  # > 300 chars
    html = f"<html><head><title>VRSF Downpipe</title></head><body><h1>VRSF Downpipe</h1><main>{body}</main></body></html>"

    _, json_path, metadata = ingest_urls.ingest_url(
        "https://www.ecstuning.com/ES1/",
        prefetched_html=html,
        provenance={"origin": "live", "trigger_query": "downpipe", "trust_score": 11},
    )
    on_disk = json.loads(Path(json_path).read_text(encoding="utf-8"))
    assert on_disk["origin"] == "live"
    assert on_disk["trigger_query"] == "downpipe"
    assert on_disk["trust_score"] == 11
    assert metadata["origin"] == "live"
