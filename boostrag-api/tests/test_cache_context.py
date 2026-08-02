import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_context_isolates_cache(tmp_path, monkeypatch):
    import answer_cache
    monkeypatch.setattr(answer_cache, "CACHE_PATH", tmp_path / "answers.json")
    answer_cache.set_cached("best dp?", {"answer": "generic"}, context="")
    answer_cache.set_cached("best dp?", {"answer": "for-BM3"}, context="BM3 tune")
    assert answer_cache.get_cached("best dp?", context="")["answer"] == "generic"
    assert answer_cache.get_cached("best dp?", context="BM3 tune")["answer"] == "for-BM3"
    assert answer_cache.get_cached("best dp?", context="different") is None


def test_default_context_still_works(tmp_path, monkeypatch):
    import answer_cache
    monkeypatch.setattr(answer_cache, "CACHE_PATH", tmp_path / "answers.json")
    answer_cache.set_cached("q", {"answer": "a"})          # no context arg (back-compat)
    assert answer_cache.get_cached("q")["answer"] == "a"
