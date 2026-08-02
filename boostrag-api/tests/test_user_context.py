import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent))
from rag_types import RetrievedContext


def _ctx():
    return [RetrievedContext(text="VRSF downpipe fits B58.", metadata={"product": "VRSF DP"}, origin="corpus", url="u")]


def test_user_context_reaches_prompt():
    import answer
    fake = MagicMock(); fake.output_text = "ans"
    with patch.object(answer.client, "responses") as resp:
        resp.create.return_value = fake
        answer.generate_answer("downpipe?", _ctx(), user_context="Drives a 2021 M340i with a BM3 tune.")
        prompt = resp.create.call_args.kwargs["input"]
    assert "BM3 tune" in prompt
    assert "2021 M340i" in prompt


def test_no_user_context_unchanged():
    import answer
    fake = MagicMock(); fake.output_text = "ans"
    with patch.object(answer.client, "responses") as resp:
        resp.create.return_value = fake
        answer.generate_answer("downpipe?", _ctx())
        prompt = resp.create.call_args.kwargs["input"]
    assert "User's build profile" not in prompt
