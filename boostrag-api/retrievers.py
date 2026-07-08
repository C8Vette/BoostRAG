from __future__ import annotations

from rag_types import RetrievedContext
from retrieve import retrieve_chunks
from research_search import tavily_research_search


class CorpusRetriever:
    """Retrieves evidence from the local ChromaDB corpus."""

    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedContext]:
        chunks = retrieve_chunks(query, top_k=top_k)
        return [
            RetrievedContext(
                text=c["text"],
                metadata=c["metadata"] or {},
                origin="corpus",
                distance=c.get("distance"),
                url=(c["metadata"] or {}).get("url"),
            )
            for c in chunks
        ]


class WebRetriever:
    """Retrieves evidence from live Tavily web search."""

    def retrieve(self, query: str, max_results: int = 5) -> list[RetrievedContext]:
        sources = tavily_research_search(query, max_results=max_results)
        return [
            RetrievedContext(
                text=s.content or "",
                metadata={"title": s.title, "url": s.url,
                          "trust_tier": s.trust_label, "score": s.score},
                origin="web",
                trust_score=s.score,
                url=s.url,
            )
            for s in sources
        ]
