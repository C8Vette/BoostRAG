import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_types import RetrievedContext


def _ctx(distance):
    return RetrievedContext(text="t", metadata={}, origin="corpus", distance=distance)


def test_sufficient_when_a_close_chunk_exists(monkeypatch):
    monkeypatch.setenv("MAX_DISTANCE", "1.0")
    monkeypatch.setenv("MIN_STRONG_CHUNKS", "1")
    from confidence import assess_corpus_confidence
    verdict = assess_corpus_confidence([_ctx(0.3), _ctx(1.8)])
    assert verdict.sufficient is True
    assert verdict.strong_chunk_count == 1
    assert verdict.nearest_distance == 0.3


def test_insufficient_when_all_chunks_far(monkeypatch):
    monkeypatch.setenv("MAX_DISTANCE", "1.0")
    monkeypatch.setenv("MIN_STRONG_CHUNKS", "1")
    from confidence import assess_corpus_confidence
    verdict = assess_corpus_confidence([_ctx(1.9), _ctx(2.2)])
    assert verdict.sufficient is False
    assert verdict.strong_chunk_count == 0


def test_insufficient_on_empty_corpus(monkeypatch):
    from confidence import assess_corpus_confidence
    verdict = assess_corpus_confidence([])
    assert verdict.sufficient is False
    assert verdict.nearest_distance is None
