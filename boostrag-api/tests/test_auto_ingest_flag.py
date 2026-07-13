import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_types import RetrievedContext


def test_flag_off_skips_ingestion(tmp_path, monkeypatch):
    import provenance
    monkeypatch.setattr(provenance, "BLACKLIST_PATH", tmp_path / "b.json")
    monkeypatch.setenv("AUTO_INGEST_ENABLED", "false")
    monkeypatch.setenv("AUTO_INGEST_MIN_SCORE", "9")
    ctx = [RetrievedContext(text="strong", metadata={"title": "A"}, origin="web",
                            trust_score=11, url="https://good.com/a")]
    with patch.object(provenance, "ingest_url") as mock_ingest:
        records = provenance.maybe_ingest_web_sources("q", ctx)
    mock_ingest.assert_not_called()
    assert records[0]["ingested"] is False
