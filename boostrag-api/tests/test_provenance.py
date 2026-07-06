import json
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_types import RetrievedContext


def _wire(tmp_path, monkeypatch):
    import provenance
    monkeypatch.setattr(provenance, "BLACKLIST_PATH", tmp_path / "blacklist.json")
    monkeypatch.setattr(provenance, "QUERIES_LOG", tmp_path / "queries.jsonl")
    monkeypatch.setattr(provenance, "COUNTER_PATH", tmp_path / "counter.json")
    return provenance


def test_blacklist_add_and_check(tmp_path, monkeypatch):
    p = _wire(tmp_path, monkeypatch)
    assert p.is_blacklisted("https://bad.com/x") is False
    p.add_to_blacklist("https://bad.com/x")
    assert p.is_blacklisted("https://bad.com/x") is True
    # domain-level match
    assert p.is_blacklisted("https://bad.com/other") is True


def test_log_answer_appends_jsonl(tmp_path, monkeypatch):
    p = _wire(tmp_path, monkeypatch)
    p.log_answer("q1", "web", "ans", [{"url": "u", "score": 9, "ingested": True}])
    p.log_answer("q2", "corpus", "ans2", [])
    lines = (tmp_path / "queries.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["query"] == "q1"


def test_daily_counter_increments(tmp_path, monkeypatch):
    p = _wire(tmp_path, monkeypatch)
    assert p.web_searches_today() == 0
    p.increment_web_search()
    p.increment_web_search()
    assert p.web_searches_today() == 2


def test_maybe_ingest_respects_trust_gate_and_blacklist(tmp_path, monkeypatch):
    p = _wire(tmp_path, monkeypatch)
    monkeypatch.setenv("AUTO_INGEST_MIN_SCORE", "9")
    p.add_to_blacklist("https://banned.com/x")
    contexts = [
        RetrievedContext(text="strong", metadata={"title": "A"}, origin="web",
                         trust_score=11, url="https://good.com/a"),
        RetrievedContext(text="weak", metadata={"title": "B"}, origin="web",
                         trust_score=3, url="https://weak.com/b"),
        RetrievedContext(text="banned", metadata={"title": "C"}, origin="web",
                         trust_score=11, url="https://banned.com/x"),
    ]
    with patch.object(p, "ingest_url") as mock_ingest:
        mock_ingest.return_value = (Path("t.txt"), Path("t.json"), {})
        records = p.maybe_ingest_web_sources("q", contexts)
    # only the good, high-score, non-blacklisted source is ingested
    assert mock_ingest.call_count == 1
    ingested = [r for r in records if r["ingested"]]
    assert len(ingested) == 1 and ingested[0]["url"] == "https://good.com/a"
