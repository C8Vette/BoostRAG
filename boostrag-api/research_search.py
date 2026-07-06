"""
Live research utilities for BoostRAG.

This module handles query expansion, web search, and lightweight source scoring.
It does not automatically add web pages to the trusted corpus.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, asdict
from typing import Any

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()


TRUSTED_AUTOMOTIVE_DOMAINS = {
    "ecstuning.com": 5,
    "turnermotorsport.com": 5,
    "dinancars.com": 5,
    "vr-speed.com": 5,
    "vrspeedfactory.com": 5,
    "burgertuning.com": 5,
    "kiesmotorsports.com": 4,
    "x-ph.com": 4,
    "bimmerpost.com": 3,
    "g20.bimmerpost.com": 3,
    "f30.bimmerpost.com": 2,
}


LOW_TRUST_PATTERNS = [
    "best-",
    "top-10",
    "top 10",
    "ai generated",
    "coupon",
    "deal",
]

LOW_TRUST_DOMAINS = {
    "aliexpress.com": -4,
    "tiktok.com": -4,
    "reddit.com": -1,
    "youtube.com": -2,
}


VEHICLE_TERMS = [
    "m340i",
    "g20",
    "b58",
    "b58tu",
    "bmw",
    "xdrive",
]


@dataclass
class ResearchSource:
    """A candidate live web source discovered during Research Mode."""

    title: str
    url: str
    content: str
    score: int
    trust_label: str
    reason: str


def normalize_domain(url: str) -> str:
    """Extract a normalized domain from a URL."""
    clean = re.sub(r"^https?://", "", url.lower())
    clean = clean.split("/")[0]
    clean = clean.replace("www.", "")
    return clean


def generate_m340i_search_queries(user_query: str) -> list[str]:
    """
    Expand a user question into targeted BMW M340i/B58 search queries.

    The goal is to improve recall for automotive terms, synonyms, and platform codes.
    """
    base = user_query.strip()

    context_terms = "BMW M340i G20 B58 B58TU"
    queries = [
        f"{context_terms} {base}",
        f"2021 BMW M340i {base}",
        f"BMW G20 M340i xDrive {base}",
    ]

    lowered = base.lower()

    # Domain-specific synonym expansion.
    if any(term in lowered for term in ["dump", "cutout", "valved", "exhaust"]):
        queries.extend(
            [
                "BMW G20 M340i xDrive valved exhaust cutout",
                "B58 M340i electronic exhaust cutout custom fabrication",
                "2021 BMW M340i exhaust dump valve xDrive clearance",
            ]
        )

    if any(term in lowered for term in ["turbo", "pure800", "pure 800"]):
        queries.extend(
            [
                "BMW M340i B58 Pure800 turbo upgrade G20",
                "B58TU M340i turbo upgrade fuel pump cooling requirements",
                "BMW G20 M340i Pure Turbos Pure800 fitment",
            ]
        )

    if any(term in lowered for term in ["downpipe", "catless", "catted", "cel"]):
        queries.extend(
            [
                "BMW M340i B58 catted downpipe CEL",
                "G20 M340i VRSF downpipe horsepower gains",
                "B58 catted vs catless downpipe check engine light",
            ]
        )

    # Deduplicate while preserving order.
    seen = set()
    unique_queries = []
    for query in queries:
        normalized = query.lower()
        if normalized not in seen:
            unique_queries.append(query)
            seen.add(normalized)

    cap = int(os.getenv("WEB_QUERY_EXPANSION", "2"))
    return unique_queries[:cap]


def score_source(title: str, url: str, content: str, user_query: str) -> tuple[int, str, str]:
    """
    Score a live web source for usefulness and trust.

    This is intentionally simple for the first implementation.
    Later, this can become a more formal source-ranker.
    """
    domain = normalize_domain(url)
    text = f"{title} {url} {content}".lower()
    query_terms = [term for term in re.findall(r"[a-zA-Z0-9]+", user_query.lower()) if len(term) > 2]

    score = 0
    reasons = []

    # Low-trust/noisy domain penalty.
    for low_domain, penalty in LOW_TRUST_DOMAINS.items():
        if low_domain in domain:
            score += penalty
            reasons.append(f"low-trust/noisy domain penalty: {low_domain}")
            break

    # Domain trust.
    for trusted_domain, weight in TRUSTED_AUTOMOTIVE_DOMAINS.items():
        if trusted_domain in domain:
            score += weight
            reasons.append(f"known automotive domain: {trusted_domain}")
            break

    # Vehicle/platform relevance.
    matched_vehicle_terms = [term for term in VEHICLE_TERMS if term in text]
    if matched_vehicle_terms:
        score += min(len(matched_vehicle_terms), 4)
        reasons.append(f"vehicle/platform terms: {', '.join(matched_vehicle_terms)}")

    # User-query term overlap.
    matched_query_terms = sorted({term for term in query_terms if term in text})
    if matched_query_terms:
        score += min(len(matched_query_terms), 5)
        reasons.append(f"query terms matched: {', '.join(matched_query_terms[:6])}")

    # Content depth.
    if len(content) > 1000:
        score += 2
        reasons.append("substantial extracted content")
    elif len(content) > 300:
        score += 1
        reasons.append("some extracted content")
    else:
        score -= 2
        reasons.append("thin extracted content")

    # Low-trust hints.
    if any(pattern in text for pattern in LOW_TRUST_PATTERNS):
        score -= 2
        reasons.append("possible low-trust/search-spam pattern")

    if score >= 9:
        trust_label = "strong_candidate"
    elif score >= 5:
        trust_label = "usable_candidate"
    elif score >= 2:
        trust_label = "weak_candidate"
    else:
        trust_label = "reject_or_manual_review"

    return score, trust_label, "; ".join(reasons) if reasons else "no strong relevance signals"


def tavily_research_search(user_query: str, max_results: int = 8) -> list[ResearchSource]:
    """
    Search the web for sources relevant to a BoostRAG user query.

    Returns ranked candidate sources. These are not automatically trusted.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY is missing. Add it to your .env file.")

    client = TavilyClient(api_key=api_key)

    queries = generate_m340i_search_queries(user_query)
    candidates: dict[str, ResearchSource] = {}

    for query in queries:
        response: dict[str, Any] = client.search(
            query=query,
            max_results=max_results,
            include_answer=False,
            include_raw_content=True,
        )

        for result in response.get("results", []):
            title = result.get("title") or "Untitled source"
            url = result.get("url") or ""
            content = result.get("raw_content") or result.get("content") or ""

            if not url:
                continue

            score, trust_label, reason = score_source(
                title=title,
                url=url,
                content=content,
                user_query=user_query,
            )

            existing = candidates.get(url)
            source = ResearchSource(
                title=title,
                url=url,
                content=content,
                score=score,
                trust_label=trust_label,
                reason=reason,
            )

            # Keep the highest-scoring version if duplicate URLs appear.
            if existing is None or source.score > existing.score:
                candidates[url] = source

    ranked = sorted(candidates.values(), key=lambda item: item.score, reverse=True)
    return ranked


def sources_as_dicts(sources: list[ResearchSource]) -> list[dict[str, Any]]:
    """Convert ResearchSource objects to JSON-serializable dictionaries."""
    return [asdict(source) for source in sources]