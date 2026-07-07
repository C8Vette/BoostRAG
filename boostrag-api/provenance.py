from __future__ import annotations

import html
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from rag_types import RetrievedContext
from ingest_urls import ingest_url

BLACKLIST_PATH = Path("data/blacklist.json")
QUERIES_LOG = Path("data/provenance/queries.jsonl")
COUNTER_PATH = Path("data/provenance/web_search_counter.json")


def _domain(url: str) -> str:
    net = urlparse(url).netloc.lower()
    return net[4:] if net.startswith("www.") else net


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def is_blacklisted(url: str) -> bool:
    data = _load_json(BLACKLIST_PATH, {"urls": [], "domains": []})
    if url in data.get("urls", []):
        return True
    return _domain(url) in data.get("domains", [])


def add_to_blacklist(url: str) -> None:
    BLACKLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = _load_json(BLACKLIST_PATH, {"urls": [], "domains": []})
    urls = data.setdefault("urls", [])
    domains = data.setdefault("domains", [])
    if url not in urls:
        urls.append(url)
    dom = _domain(url)
    if dom not in domains:
        domains.append(dom)
    BLACKLIST_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def log_answer(query: str, origin: str, answer: str, sources: list[dict]) -> None:
    QUERIES_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "origin": origin,
        "answer_preview": (answer or "")[:200],
        "sources": sources,
    }
    with QUERIES_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def web_searches_today() -> int:
    data = _load_json(COUNTER_PATH, {})
    return int(data.get(date.today().isoformat(), 0))


def increment_web_search() -> None:
    COUNTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = _load_json(COUNTER_PATH, {})
    today = date.today().isoformat()
    data[today] = int(data.get(today, 0)) + 1
    COUNTER_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _text_to_html(title: str, body: str) -> str:
    return (
        f"<html><head><title>{html.escape(title)}</title></head>"
        f"<body><h1>{html.escape(title)}</h1>"
        f"<main>{html.escape(body)}</main></body></html>"
    )


def maybe_ingest_web_sources(query: str, contexts: list[RetrievedContext]) -> list[dict]:
    """Auto-ingest high-trust, non-blacklisted web sources. Returns per-source records."""
    min_score = float(os.getenv("AUTO_INGEST_MIN_SCORE", "9"))
    records: list[dict] = []
    for ctx in contexts:
        url = ctx.url or ""
        score = ctx.trust_score if ctx.trust_score is not None else -999
        ingested = False
        route = None
        if url and score >= min_score and not is_blacklisted(url):
            title = ctx.metadata.get("title", "Live Web Source")
            try:
                _, _, meta = ingest_url(
                    url,
                    prefetched_html=_text_to_html(title, ctx.text),
                    provenance={
                        "origin": "live",
                        "trigger_query": query,
                        "trust_score": score,
                        "ingested_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                route = meta.get("route")
                ingested = (route == "cleaned")
            except Exception:
                route = None
                ingested = False  # thin/blocked content — best-effort, never raises
        records.append({"url": url, "score": score, "ingested": ingested, "route": route})
    return records
