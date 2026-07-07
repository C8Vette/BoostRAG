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

NO_ANSWER = "I don't have a good answer for this yet."


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
        out.append({
            "product": meta.get("product", meta.get("title")),
            "url": c.url or meta.get("url"),
            "origin": c.origin,
            "trust_tier": meta.get("trust_tier"),
            "price": meta.get("price"),
            "text_preview": (c.text or "")[:350],
        })
    return out


def answer_question(query: str, top_k: int = 3) -> AnswerResult:
    cached = get_cached(query)
    if cached:
        return AnswerResult(**cached)

    corpus_ctx = CorpusRetriever().retrieve(query, top_k=top_k)
    verdict = assess_corpus_confidence(corpus_ctx)
    confidence = {"sufficient": verdict.sufficient,
                  "nearest_distance": verdict.nearest_distance}

    # Corpus is confident -> answer from it.
    if verdict.sufficient:
        return _corpus_answer(query, corpus_ctx, confidence, cache=True)

    # Corpus weak -> try web if the daily fuse allows it.
    cap = int(os.getenv("DAILY_WEB_SEARCH_CAP", "15"))
    if web_searches_today() < cap:
        increment_web_search()
        web_ctx = WebRetriever().retrieve(query)
        if web_ctx:
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

    # Fuse tripped or no web results -> best corpus answer, else honest none.
    if corpus_ctx:
        return _corpus_answer(query, corpus_ctx, confidence, cache=False)

    log_answer(query, "none", NO_ANSWER, [])
    return AnswerResult(NO_ANSWER, "none", [], confidence)
