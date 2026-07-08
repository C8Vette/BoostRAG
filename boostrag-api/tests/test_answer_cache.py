import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_set_then_get_roundtrip(tmp_path, monkeypatch):
    import answer_cache
    monkeypatch.setattr(answer_cache, "CACHE_PATH", tmp_path / "answers.json")
    answer_cache.set_cached("Best Downpipe?", {"answer": "VRSF", "origin": "web"})
    # normalization: different case/spacing hits the same entry
    got = answer_cache.get_cached("best   downpipe?")
    assert got["answer"] == "VRSF"


def test_miss_returns_none(tmp_path, monkeypatch):
    import answer_cache
    monkeypatch.setattr(answer_cache, "CACHE_PATH", tmp_path / "answers.json")
    assert answer_cache.get_cached("nothing here") is None


def test_expired_entry_is_ignored(tmp_path, monkeypatch):
    import answer_cache
    monkeypatch.setattr(answer_cache, "CACHE_PATH", tmp_path / "answers.json")
    monkeypatch.setenv("CACHE_TTL_HOURS", "0")  # everything immediately stale
    answer_cache.set_cached("q", {"answer": "a"})
    time.sleep(0.01)
    assert answer_cache.get_cached("q") is None
