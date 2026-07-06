import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_score_source_penalizes_low_trust_domain_without_crashing():
    from research_search import score_source
    # reddit.com is a low-trust domain; before the fix this raised UnboundLocalError
    score, label, reason = score_source(
        title="M340i downpipe thread",
        url="https://www.reddit.com/r/BMW/comments/abc",
        content="Discussion about B58 M340i downpipe options and CEL.",
        user_query="best downpipe for M340i",
    )
    assert isinstance(score, int)
    assert "low-trust" in reason.lower()


def test_score_source_rewards_trusted_domain():
    from research_search import score_source
    score, label, reason = score_source(
        title="VRSF Downpipe",
        url="https://www.ecstuning.com/b-vrsf/ES123/",
        content="VRSF catted downpipe for BMW M340i G20 B58.",
        user_query="downpipe M340i",
    )
    assert score >= 5
    assert "ecstuning.com" in reason


def test_query_expansion_respects_env_cap(monkeypatch):
    monkeypatch.setenv("WEB_QUERY_EXPANSION", "2")
    from importlib import reload
    import research_search
    reload(research_search)
    queries = research_search.generate_m340i_search_queries("downpipe options")
    assert len(queries) == 2


def test_tavily_prefers_raw_content(monkeypatch):
    import research_search
    fake_response = {
        "results": [
            {"title": "T", "url": "https://www.ecstuning.com/ES1/",
             "content": "short snippet",
             "raw_content": "a much longer body of extracted page text " * 10},
        ]
    }

    class FakeClient:
        def __init__(self, api_key): pass
        def search(self, **kwargs):
            assert kwargs.get("include_raw_content") is True
            return fake_response

    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("WEB_QUERY_EXPANSION", "1")
    monkeypatch.setattr(research_search, "TavilyClient", FakeClient)
    results = research_search.tavily_research_search("downpipe", max_results=1)
    assert results
    assert "longer body" in results[0].content
