import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_types import RetrievedContext


def test_tier_for_url_maps_domains():
    from source_ranker import tier_for_url
    assert tier_for_url("https://www.ecstuning.com/b-x/ES1/") == "Tier 1"
    assert tier_for_url("https://g20.bimmerpost.com/forums/thread") == "Tier 2"
    assert tier_for_url("https://some-unknown-shop.example/x") == "Tier 3"


def test_corpus_sources_get_domain_derived_tier():
    import orchestrator
    ctx = [RetrievedContext(text="body", metadata={"product": "P", "url": "https://www.ecstuning.com/ES1/"},
                            origin="corpus", url="https://www.ecstuning.com/ES1/")]
    out = orchestrator._sources_from_contexts(ctx)
    assert out[0]["trust_tier"] == "Tier 1"


def test_web_sources_keep_research_label():
    import orchestrator
    ctx = [RetrievedContext(text="body", metadata={"title": "T", "url": "https://x/1", "trust_tier": "usable_candidate"},
                            origin="web", url="https://x/1")]
    out = orchestrator._sources_from_contexts(ctx)
    assert out[0]["trust_tier"] == "usable_candidate"


def test_looks_insufficient_handles_typographic_apostrophe():
    import orchestrator
    # the model emits a curly apostrophe (U+2019), not a straight one
    assert orchestrator._looks_insufficient("I couldn’t find that in the retrieved evidence.") is True
    assert orchestrator._looks_insufficient("The VRSF downpipe fits the B58 M340i.") is False
