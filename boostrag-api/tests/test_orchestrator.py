import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_types import RetrievedContext, Verdict


def _patch_common(orch, monkeypatch, tmp_path):
    # isolate cache + provenance side effects
    import answer_cache, provenance
    monkeypatch.setattr(answer_cache, "CACHE_PATH", tmp_path / "c.json")
    monkeypatch.setattr(provenance, "QUERIES_LOG", tmp_path / "q.jsonl")
    monkeypatch.setattr(provenance, "COUNTER_PATH", tmp_path / "n.json")
    monkeypatch.setattr(provenance, "BLACKLIST_PATH", tmp_path / "b.json")


def test_corpus_path_when_confident(tmp_path, monkeypatch):
    import orchestrator, answer_cache
    _patch_common(orchestrator, monkeypatch, tmp_path)
    corpus_ctx = [RetrievedContext(text="body", metadata={"product": "P", "url": "u"},
                                   origin="corpus", distance=0.3)]
    with patch.object(orchestrator.CorpusRetriever, "retrieve", return_value=corpus_ctx), \
         patch.object(orchestrator, "assess_corpus_confidence",
                      return_value=Verdict(True, 0.3, 1)), \
         patch.object(orchestrator, "generate_answer", return_value="corpus answer") as gen, \
         patch.object(orchestrator.WebRetriever, "retrieve") as web:
        result = orchestrator.answer_question("q")
    assert result.origin == "corpus"
    assert result.answer == "corpus answer"
    web.assert_not_called()
    assert answer_cache.get_cached("q") is not None


def test_web_fallback_when_corpus_weak(tmp_path, monkeypatch):
    import orchestrator
    _patch_common(orchestrator, monkeypatch, tmp_path)
    monkeypatch.setenv("DAILY_WEB_SEARCH_CAP", "15")
    web_ctx = [RetrievedContext(text="web body", metadata={"title": "T", "url": "wu"},
                                origin="web", trust_score=11, url="wu")]
    with patch.object(orchestrator.CorpusRetriever, "retrieve", return_value=[]), \
         patch.object(orchestrator, "assess_corpus_confidence",
                      return_value=Verdict(False, None, 0)), \
         patch.object(orchestrator.WebRetriever, "retrieve", return_value=web_ctx), \
         patch.object(orchestrator, "generate_answer", return_value="web answer"), \
         patch.object(orchestrator, "maybe_ingest_web_sources",
                      return_value=[{"url": "wu", "score": 11, "ingested": True}]) as ing:
        result = orchestrator.answer_question("q")
    assert result.origin == "web"
    ing.assert_called_once()


def test_daily_fuse_blocks_web(tmp_path, monkeypatch):
    import orchestrator, provenance
    _patch_common(orchestrator, monkeypatch, tmp_path)
    monkeypatch.setenv("DAILY_WEB_SEARCH_CAP", "0")  # fuse already blown
    with patch.object(orchestrator.CorpusRetriever, "retrieve", return_value=[]), \
         patch.object(orchestrator, "assess_corpus_confidence",
                      return_value=Verdict(False, None, 0)), \
         patch.object(orchestrator.WebRetriever, "retrieve") as web:
        result = orchestrator.answer_question("q")
    web.assert_not_called()
    assert result.origin == "none"


def test_cache_short_circuits(tmp_path, monkeypatch):
    import orchestrator, answer_cache
    _patch_common(orchestrator, monkeypatch, tmp_path)
    answer_cache.set_cached("q", {"answer": "cached", "origin": "web",
                                  "sources": [], "confidence": {}})
    with patch.object(orchestrator.CorpusRetriever, "retrieve") as corpus:
        result = orchestrator.answer_question("q")
    corpus.assert_not_called()
    assert result.answer == "cached"


def test_web_empty_falls_back_to_corpus(tmp_path, monkeypatch):
    import orchestrator
    _patch_common(orchestrator, monkeypatch, tmp_path)
    monkeypatch.setenv("DAILY_WEB_SEARCH_CAP", "15")
    corpus_ctx = [RetrievedContext(text="body", metadata={"product": "P", "url": "u"},
                                   origin="corpus", distance=1.5)]
    with patch.object(orchestrator.CorpusRetriever, "retrieve", return_value=corpus_ctx), \
         patch.object(orchestrator, "assess_corpus_confidence",
                      return_value=Verdict(False, 1.5, 0)), \
         patch.object(orchestrator.WebRetriever, "retrieve", return_value=[]), \
         patch.object(orchestrator, "generate_answer", return_value="corpus fallback answer"), \
         patch.object(orchestrator, "maybe_ingest_web_sources") as ing:
        result = orchestrator.answer_question("q")
    assert result.origin == "corpus"
    assert result.answer == "corpus fallback answer"
    ing.assert_not_called()


def test_confident_but_insufficient_answer_escalates_to_web(tmp_path, monkeypatch):
    import orchestrator
    _patch_common(orchestrator, monkeypatch, tmp_path)
    monkeypatch.setenv("DAILY_WEB_SEARCH_CAP", "15")
    corpus_ctx = [RetrievedContext(text="body", metadata={"product": "P", "url": "u"},
                                   origin="corpus", distance=0.88)]
    web_ctx = [RetrievedContext(text="web body", metadata={"title": "T", "url": "wu"},
                                origin="web", trust_score=11, url="wu")]
    with patch.object(orchestrator.CorpusRetriever, "retrieve", return_value=corpus_ctx), \
         patch.object(orchestrator, "assess_corpus_confidence",
                      return_value=Verdict(True, 0.88, 1)), \
         patch.object(orchestrator, "generate_answer",
                      side_effect=["I couldn't find that in the retrieved evidence.", "web answer"]), \
         patch.object(orchestrator.WebRetriever, "retrieve", return_value=web_ctx), \
         patch.object(orchestrator, "maybe_ingest_web_sources",
                      return_value=[{"url": "wu", "score": 11, "ingested": True}]):
        result = orchestrator.answer_question("q")
    assert result.origin == "web"
    assert result.answer == "web answer"


def test_confident_sufficient_answer_does_not_escalate(tmp_path, monkeypatch):
    import orchestrator
    _patch_common(orchestrator, monkeypatch, tmp_path)
    monkeypatch.setenv("DAILY_WEB_SEARCH_CAP", "15")
    corpus_ctx = [RetrievedContext(text="body", metadata={"product": "P", "url": "u"},
                                   origin="corpus", distance=0.3)]
    with patch.object(orchestrator.CorpusRetriever, "retrieve", return_value=corpus_ctx), \
         patch.object(orchestrator, "assess_corpus_confidence",
                      return_value=Verdict(True, 0.3, 1)), \
         patch.object(orchestrator, "generate_answer", return_value="corpus answer"), \
         patch.object(orchestrator.WebRetriever, "retrieve") as web:
        result = orchestrator.answer_question("q")
    assert result.origin == "corpus"
    web.assert_not_called()


def test_fuse_degraded_corpus_answer_is_not_cached(tmp_path, monkeypatch):
    import orchestrator, answer_cache
    _patch_common(orchestrator, monkeypatch, tmp_path)
    monkeypatch.setenv("DAILY_WEB_SEARCH_CAP", "0")  # fuse already blown
    corpus_ctx = [RetrievedContext(text="body", metadata={"product": "P", "url": "u"},
                                   origin="corpus", distance=1.5)]
    with patch.object(orchestrator.CorpusRetriever, "retrieve", return_value=corpus_ctx), \
         patch.object(orchestrator, "assess_corpus_confidence",
                      return_value=Verdict(False, 1.5, 0)), \
         patch.object(orchestrator.WebRetriever, "retrieve") as web, \
         patch.object(orchestrator, "generate_answer", return_value="degraded corpus answer"):
        result = orchestrator.answer_question("q")
    web.assert_not_called()
    assert result.origin == "corpus"
    assert result.answer == "degraded corpus answer"
    assert answer_cache.get_cached("q") is None
