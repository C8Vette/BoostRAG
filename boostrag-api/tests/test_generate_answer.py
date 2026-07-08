import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_types import RetrievedContext


def test_generate_answer_builds_prompt_from_contexts_and_returns_text():
    import answer
    ctx = [RetrievedContext(
        text="VRSF catted downpipe fits B58 M340i.",
        metadata={"product": "VRSF Downpipe", "url": "https://x/ES1/"},
        origin="web", url="https://x/ES1/")]

    fake = MagicMock()
    fake.output_text = "  The VRSF downpipe fits your M340i.  "
    with patch.object(answer.client, "responses") as resp:
        resp.create.return_value = fake
        out = answer.generate_answer("what downpipe fits?", ctx)
        # the model was called with a prompt containing the evidence text
        sent_prompt = resp.create.call_args.kwargs["input"]
        assert "VRSF catted downpipe" in sent_prompt
    assert out == "The VRSF downpipe fits your M340i."
