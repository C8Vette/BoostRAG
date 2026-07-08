from __future__ import annotations

import os

from rag_types import RetrievedContext, AnswerResult
from retrievers import CorpusRetriever, WebRetriever
from confidence import assess_corpus_confidence
from answer import generate_answer
from answer_cache import get_cached, set_cached
from provenance import (
    log_answer,
    web_searches_today,
    increment_web_search,
    maybe_ingest_web_sources,
)
from source_ranker import tier_for_url

NO_ANSWER = "I don't have a good answer for this yet."

INSUFFICIENT_MARKERS = (
    "not stated",
    "couldn't find",
    "could not find",
    "insufficient evidence",
    "not enough information",
    "not enough evidence",
    "do not have enough",
    "don't have enough",
    "no relevant information",
    "not in the retrieved evidence",
)


def _looks_insufficient(answer: str) -> bool:
    """True if a grounded answer admits the evidence didn't cover the question.

    Normalizes the typographic apostrophe (U+2019) the model emits so markers
    like "couldn't find" match regardless of quote style.
    """
    low = (answer or "").lower().replace("’", "'")
    return any(marker in low for marker in INSUFFICIENT_MARKERS)


def _corpus_answer(
    query: str,
    corpus_ctx: list[RetrievedContext],
    confidence: dict,
    *,
    cache: bool,
) -> AnswerResult:
    answer = generate_answer(query, corpus_ctx)
    sources = _sources_from_contexts(corpus_ctx)
    log_answer(query, "corpus", answer, sources)
    result = AnswerResult(answer, "corpus", sources, confidence)
    if cache:
        set_cached(query, result.__dict__)
    return result


def _sources_from_contexts(contexts: list[RetrievedContext]) -> list[dict]:
    out = []
    for c in contexts:
        meta = c.metadata or {}
        url = c.url or meta.get("url")
        # Web sources carry the research scorer's label; corpus sources derive
        # their tier from the domain at query time (legacy files lack the header).
        if c.origin == "corpus":
            trust_tier = tier_for_url(url) if url else None
        else:
            trust_tier = meta.get("trust_tier")
        out.append({
            "product": meta.get("product", meta.get("title")),
            "url": url,
            "origin": c.origin,
            "trust_tier": trust_tier,
            "price": meta.get("price"),
            "text_preview": (c.text or "")[:350],
        })
    return out


def _try_web_answer(query: str, confidence: dict) -> AnswerResult | None:
    """Attempt a web-sourced answer. Returns None if the daily fuse is blown or web has nothing."""
    cap = int(os.getenv("DAILY_WEB_SEARCH_CAP", "15"))
    if web_searches_today() >= cap:
        return None
    increment_web_search()
    web_ctx = WebRetriever().retrieve(query)
    if not web_ctx:
        return None
    answer = generate_answer(query, web_ctx)
    sources = _sources_from_contexts(web_ctx)
    ingest_records = maybe_ingest_web_sources(query, web_ctx)
    logged_sources = [
        {**s, "ingested": rec["ingested"]}
        for s, rec in zip(sources, ingest_records)
    ]
    log_answer(query, "web", answer, logged_sources)
    result = AnswerResult(answer, "web", sources, confidence)
    set_cached(query, result.__dict__)
    return result


def answer_question(query: str, top_k: int = 3) -> AnswerResult:
    cached = get_cached(query)
    if cached:
        return AnswerResult(**cached)

    corpus_ctx = CorpusRetriever().retrieve(query, top_k=top_k)
    verdict = assess_corpus_confidence(corpus_ctx)
    confidence = {"sufficient": verdict.sufficient,
                  "nearest_distance": verdict.nearest_distance}

    if verdict.sufficient:
        answer = generate_answer(query, corpus_ctx)
        insufficient = _looks_insufficient(answer)
        if insufficient:
            web = _try_web_answer(query, confidence)
            if web is not None:
                return web
        sources = _sources_from_contexts(corpus_ctx)
        log_answer(query, "corpus", answer, sources)
        result = AnswerResult(answer, "corpus", sources, confidence)
        if not insufficient:
            set_cached(query, result.__dict__)
        return result

    web = _try_web_answer(query, confidence)
    if web is not None:
        return web

    if corpus_ctx:
        return _corpus_answer(query, corpus_ctx, confidence, cache=False)

    log_answer(query, "none", NO_ANSWER, [])
    return AnswerResult(NO_ANSWER, "none", [], confidence)
