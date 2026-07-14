import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import orchestrator


def test_live_observed_refusal_phrasings_escalate():
    """Exact phrasings seen on the deployed site that previously stayed on the
    corpus path because the marker list didn't include 'can't determine/answer'."""
    assert orchestrator._looks_insufficient(
        "I can't determine the BMW M340i B58 engine oil weight or oil capacity from the retrieved evidence.")
    assert orchestrator._looks_insufficient(
        "I can't determine the best all-season tires for the BMW M340i from the retrieved evidence.")
    assert orchestrator._looks_insufficient(
        "I can't answer that confidently from the evidence provided.")


def test_substantive_corpus_answer_does_not_escalate():
    """A real, answered corpus response must NOT be treated as insufficient."""
    assert not orchestrator._looks_insufficient(
        "The VRSF catted downpipe fits the B58 M340i, reduces backpressure for faster "
        "spool, and comes in race or high-flow catted configurations.")
