import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))
from rag_types import RetrievedContext, Verdict


def test_user_context_flows_to_generate_and_cache(tmp_path, monkeypatch):
    import answer_cache, provenance, orchestrator
    monkeypatch.setattr(answer_cache, "CACHE_PATH", tmp_path / "c.json")
    monkeypatch.setattr(provenance, "QUERIES_LOG", tmp_path / "q.jsonl")
    corpus = [RetrievedContext(text="b", metadata={"product": "P", "url": "u"}, origin="corpus", distance=0.3)]
    with patch.object(orchestrator.CorpusRetriever, "retrieve", return_value=corpus), \
         patch.object(orchestrator, "assess_corpus_confidence", return_value=Verdict(True, 0.3, 1)), \
         patch.object(orchestrator, "generate_answer", return_value="ok") as gen, \
         patch.object(orchestrator, "set_cached") as setc:
        orchestrator.answer_question("q", user_context="BM3 tune")
    assert gen.call_args.kwargs.get("user_context") == "BM3 tune"
    assert setc.call_args.kwargs.get("context") == "BM3 tune"
