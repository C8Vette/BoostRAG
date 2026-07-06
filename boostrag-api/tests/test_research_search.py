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
