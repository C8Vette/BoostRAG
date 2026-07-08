from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetrievedContext:
    """A unit of evidence from any retriever (corpus or web)."""
    text: str
    metadata: dict
    origin: str                      # "corpus" | "web"
    trust_score: float | None = None
    distance: float | None = None
    url: str | None = None


@dataclass
class Verdict:
    """Result of assessing whether the corpus can answer confidently."""
    sufficient: bool
    nearest_distance: float | None
    strong_chunk_count: int


@dataclass
class AnswerResult:
    """Final answer plus provenance for the API layer."""
    answer: str
    origin: str                      # "corpus" | "web" | "none"
    sources: list[dict]
    confidence: dict
