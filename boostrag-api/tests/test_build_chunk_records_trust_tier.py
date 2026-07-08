import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from chunk_embed import build_chunk_records


def test_trust_tier_copied_into_metadata():
    docs = [{"text": "some body text", "trust_tier": "Tier 1", "product": "P", "url": "u"}]
    records = build_chunk_records(docs)
    assert records[0]["metadata"]["trust_tier"] == "Tier 1"


def test_missing_trust_tier_defaults_to_empty_string():
    docs = [{"text": "some body text", "product": "P", "url": "u"}]
    records = build_chunk_records(docs)
    assert records[0]["metadata"]["trust_tier"] == ""
