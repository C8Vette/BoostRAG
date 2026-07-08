import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_corpus_retriever_maps_chunks_to_contexts():
    import retrievers
    fake_chunks = [{"id": "1", "text": "body", "distance": 0.4,
                    "metadata": {"url": "https://x/ES1/", "product": "P"}}]
    with patch.object(retrievers, "retrieve_chunks", return_value=fake_chunks):
        out = retrievers.CorpusRetriever().retrieve("q", top_k=1)
    assert len(out) == 1
    assert out[0].origin == "corpus"
    assert out[0].distance == 0.4
    assert out[0].url == "https://x/ES1/"


def test_web_retriever_maps_research_sources_to_contexts():
    import retrievers
    from research_search import ResearchSource
    fake = [ResearchSource(title="T", url="https://x/ES1/", content="web body",
                           score=11, trust_label="strong_candidate", reason="r")]
    with patch.object(retrievers, "tavily_research_search", return_value=fake):
        out = retrievers.WebRetriever().retrieve("q")
    assert out[0].origin == "web"
    assert out[0].trust_score == 11
    assert out[0].metadata["trust_tier"] == "strong_candidate"
    assert out[0].text == "web body"
