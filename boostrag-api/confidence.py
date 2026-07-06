from __future__ import annotations

import os

from rag_types import RetrievedContext, Verdict


def assess_corpus_confidence(contexts: list[RetrievedContext]) -> Verdict:
    """Decide whether the local corpus can answer confidently, from chunk distances."""
    max_distance = float(os.getenv("MAX_DISTANCE", "1.0"))
    min_strong = int(os.getenv("MIN_STRONG_CHUNKS", "1"))

    distances = [c.distance for c in contexts if c.distance is not None]
    strong = [d for d in distances if d <= max_distance]
    nearest = min(distances) if distances else None

    return Verdict(
        sufficient=len(strong) >= min_strong,
        nearest_distance=nearest,
        strong_chunk_count=len(strong),
    )
