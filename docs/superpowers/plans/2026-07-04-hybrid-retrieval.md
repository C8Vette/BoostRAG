# Hybrid Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let BoostRAG answer questions outside its curated corpus by auto-falling-back to live web search, with honest source labeling and an autonomous, auditable corpus-growth flywheel.

**Architecture:** A deterministic `orchestrator.py` sits behind `/ask`. It checks a cache, retrieves from the local corpus (ChromaDB), scores confidence by embedding distance, and — only when the corpus is weak — falls through to Tavily web search. Both paths run through one grounded generator. After a web answer, high-trust sources auto-ingest (provenance-tagged) and every answer is logged. Corpus and web retrievers share one `retrieve()` contract so agentic retrieval can slot in later.

**Tech Stack:** Python 3.12, FastAPI, ChromaDB, OpenAI (`gpt-5.4-mini`, `text-embedding-3-small`), Tavily, BeautifulSoup/lxml, pytest.

## Global Constraints

- Run all Python via `./.venv/Scripts/python.exe` from `boostrag-api/` (Windows venv).
- Run tests via `./.venv/Scripts/python.exe -m pytest` from `boostrag-api/`.
- No live API calls in tests — Tavily and OpenAI are ALWAYS mocked. Suite must be free and offline.
- Storage is flat files under `boostrag-api/data/` — no new database.
- All tuning knobs are env vars with these defaults: `MAX_DISTANCE=1.0`, `MIN_STRONG_CHUNKS=1`, `WEB_QUERY_EXPANSION=2`, `DAILY_WEB_SEARCH_CAP=15`, `AUTO_INGEST_MIN_SCORE=9`, `CACHE_TTL_HOURS=24`.
- Commit messages: no "Co-Authored-By" trailer; concise.
- Existing 18 `tests/test_ecs_scraper.py` tests must stay green throughout.
- **Preflight (run once before Task 1):** `./.venv/Scripts/python.exe -c "import tavily, dotenv, httpx"` — the import chain (`orchestrator` → `research_search` → `tavily`; `answer` → `dotenv`; API tests → `httpx`) requires all three. If any error, `./.venv/Scripts/python.exe -m pip install tavily-python python-dotenv httpx`.

---

## File Structure

**New files (`boostrag-api/`):**
- `rag_types.py` — shared dataclasses: `RetrievedContext`, `Verdict`, `AnswerResult`.
- `confidence.py` — `assess_corpus_confidence()`.
- `retrievers.py` — `CorpusRetriever`, `WebRetriever` (the `retrieve()` contract).
- `answer_cache.py` — JSON file answer cache.
- `provenance.py` — paper-trail log, blacklist, daily counter, auto-ingest.
- `orchestrator.py` — the decision flow.
- `purge_source.py` — CLI to remove + blacklist a bad source.

**Modified files:**
- `research_search.py` — fix `score_source` bug; cap query expansion; prefer raw content.
- `answer.py` — add `generate_answer(query, contexts)`.
- `ingest_urls.py` — add `provenance` kwarg to `ingest_url`.
- `main.py` — call orchestrator; extend response models.
- `boostrag-frontend/src/App.jsx` — origin badge, trust chips, `none` state.

**Test files (all under `boostrag-api/tests/`):** one per module below.

---

## Task 1: Fix the `score_source` bug in research_search.py

**Files:**
- Modify: `boostrag-api/research_search.py:140-164`
- Test: `boostrag-api/tests/test_research_search.py`

**Interfaces:**
- Produces: `score_source(title, url, content, user_query) -> tuple[int, str, str]` (unchanged signature, now correct).

- [ ] **Step 1: Write the failing test**

Create `boostrag-api/tests/test_research_search.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_score_source_penalizes_low_trust_domain_without_crashing():
    from research_search import score_source
    # reddit.com is a low-trust domain; before the fix this raised UnboundLocalError
    score, label, reason = score_source(
        title="M340i downpipe thread",
        url="https://www.reddit.com/r/BMW/comments/abc",
        content="Discussion about B58 M340i downpipe options and CEL.",
        user_query="best downpipe for M340i",
    )
    assert isinstance(score, int)
    assert "low-trust" in reason.lower()


def test_score_source_rewards_trusted_domain():
    from research_search import score_source
    score, label, reason = score_source(
        title="VRSF Downpipe",
        url="https://www.ecstuning.com/b-vrsf/ES123/",
        content="VRSF catted downpipe for BMW M340i G20 B58.",
        user_query="downpipe M340i",
    )
    assert score >= 5
    assert "ecstuning.com" in reason
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_research_search.py -v`
Expected: `test_score_source_penalizes_low_trust_domain_without_crashing` FAILS with `UnboundLocalError: local variable 'score' referenced before assignment`.

- [ ] **Step 3: Fix the bug**

In `research_search.py`, move initialization above the low-trust loop. Replace lines ~147-157 (the block from `domain = normalize_domain(url)` through `reasons = []`) with this exact order:
```python
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
```
Leave the rest of the function (domain trust, vehicle terms, query overlap, content depth, trust label) unchanged.

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_research_search.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add boostrag-api/research_search.py boostrag-api/tests/test_research_search.py
git commit -m "fix: initialize score/reasons before use in score_source"
```

---

## Task 2: Cap query expansion + prefer raw content in research_search.py

**Files:**
- Modify: `boostrag-api/research_search.py` (`generate_m340i_search_queries`, `tavily_research_search`)
- Test: `boostrag-api/tests/test_research_search.py`

**Interfaces:**
- Produces: `generate_m340i_search_queries(user_query)` now honors env `WEB_QUERY_EXPANSION` (default 2). `tavily_research_search(user_query, max_results=8)` requests raw content and stores it in `ResearchSource.content`.

- [ ] **Step 1: Write the failing test**

Append to `boostrag-api/tests/test_research_search.py`:
```python
def test_query_expansion_respects_env_cap(monkeypatch):
    monkeypatch.setenv("WEB_QUERY_EXPANSION", "2")
    from importlib import reload
    import research_search
    reload(research_search)
    queries = research_search.generate_m340i_search_queries("downpipe options")
    assert len(queries) == 2


def test_tavily_prefers_raw_content(monkeypatch):
    import research_search
    fake_response = {
        "results": [
            {"title": "T", "url": "https://www.ecstuning.com/ES1/",
             "content": "short snippet",
             "raw_content": "a much longer body of extracted page text " * 10},
        ]
    }

    class FakeClient:
        def __init__(self, api_key): pass
        def search(self, **kwargs):
            assert kwargs.get("include_raw_content") is True
            return fake_response

    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("WEB_QUERY_EXPANSION", "1")
    monkeypatch.setattr(research_search, "TavilyClient", FakeClient)
    results = research_search.tavily_research_search("downpipe", max_results=1)
    assert results
    assert "longer body" in results[0].content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_research_search.py -k "expansion or raw_content" -v`
Expected: FAIL (expansion still returns up to 6; `include_raw_content` currently False).

- [ ] **Step 3: Implement**

In `generate_m340i_search_queries`, replace the final `return unique_queries[:6]` with:
```python
    import os
    cap = int(os.getenv("WEB_QUERY_EXPANSION", "2"))
    return unique_queries[:cap]
```
In `tavily_research_search`, change the `client.search(...)` call to include `include_raw_content=True`:
```python
        response: dict[str, Any] = client.search(
            query=query,
            max_results=max_results,
            include_answer=False,
            include_raw_content=True,
        )
```
And change the content extraction line from `content = result.get("content") or ""` to:
```python
            content = result.get("raw_content") or result.get("content") or ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_research_search.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add boostrag-api/research_search.py boostrag-api/tests/test_research_search.py
git commit -m "feat: cap web query expansion and prefer Tavily raw content"
```

---

## Task 3: Shared retrieval types (`rag_types.py`)

**Files:**
- Create: `boostrag-api/rag_types.py`
- Test: `boostrag-api/tests/test_rag_types.py`

**Interfaces:**
- Produces:
  - `RetrievedContext(text: str, metadata: dict, origin: str, trust_score: float|None=None, distance: float|None=None, url: str|None=None)`
  - `Verdict(sufficient: bool, nearest_distance: float|None, strong_chunk_count: int)`
  - `AnswerResult(answer: str, origin: str, sources: list[dict], confidence: dict)`

- [ ] **Step 1: Write the failing test**

Create `boostrag-api/tests/test_rag_types.py`:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_retrieved_context_defaults():
    from rag_types import RetrievedContext
    c = RetrievedContext(text="t", metadata={"url": "u"}, origin="corpus")
    assert c.trust_score is None and c.distance is None and c.url is None


def test_answer_result_shape():
    from rag_types import AnswerResult
    r = AnswerResult(answer="a", origin="web", sources=[], confidence={"sufficient": False})
    assert r.origin == "web" and r.sources == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rag_types.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rag_types'`.

- [ ] **Step 3: Implement**

Create `boostrag-api/rag_types.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rag_types.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add boostrag-api/rag_types.py boostrag-api/tests/test_rag_types.py
git commit -m "feat: add shared retrieval dataclasses"
```

---

## Task 4: Confidence assessment (`confidence.py`)

**Files:**
- Create: `boostrag-api/confidence.py`
- Test: `boostrag-api/tests/test_confidence.py`

**Interfaces:**
- Consumes: `RetrievedContext` (Task 3).
- Produces: `assess_corpus_confidence(contexts: list[RetrievedContext]) -> Verdict`.

- [ ] **Step 1: Write the failing test**

Create `boostrag-api/tests/test_confidence.py`:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_types import RetrievedContext


def _ctx(distance):
    return RetrievedContext(text="t", metadata={}, origin="corpus", distance=distance)


def test_sufficient_when_a_close_chunk_exists(monkeypatch):
    monkeypatch.setenv("MAX_DISTANCE", "1.0")
    monkeypatch.setenv("MIN_STRONG_CHUNKS", "1")
    from confidence import assess_corpus_confidence
    verdict = assess_corpus_confidence([_ctx(0.3), _ctx(1.8)])
    assert verdict.sufficient is True
    assert verdict.strong_chunk_count == 1
    assert verdict.nearest_distance == 0.3


def test_insufficient_when_all_chunks_far(monkeypatch):
    monkeypatch.setenv("MAX_DISTANCE", "1.0")
    monkeypatch.setenv("MIN_STRONG_CHUNKS", "1")
    from confidence import assess_corpus_confidence
    verdict = assess_corpus_confidence([_ctx(1.9), _ctx(2.2)])
    assert verdict.sufficient is False
    assert verdict.strong_chunk_count == 0


def test_insufficient_on_empty_corpus(monkeypatch):
    from confidence import assess_corpus_confidence
    verdict = assess_corpus_confidence([])
    assert verdict.sufficient is False
    assert verdict.nearest_distance is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_confidence.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'confidence'`.

- [ ] **Step 3: Implement**

Create `boostrag-api/confidence.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_confidence.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add boostrag-api/confidence.py boostrag-api/tests/test_confidence.py
git commit -m "feat: add corpus confidence assessment"
```

---

## Task 5: Grounded generator refactor (`answer.py`)

**Files:**
- Modify: `boostrag-api/answer.py` (add function; keep existing `answer_query`)
- Test: `boostrag-api/tests/test_generate_answer.py`

**Interfaces:**
- Consumes: `RetrievedContext` (Task 3).
- Produces: `generate_answer(query: str, contexts: list[RetrievedContext]) -> str`.

- [ ] **Step 1: Write the failing test**

Create `boostrag-api/tests/test_generate_answer.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_generate_answer.py -v`
Expected: FAIL with `AttributeError: module 'answer' has no attribute 'generate_answer'`.

- [ ] **Step 3: Implement**

In `boostrag-api/answer.py`, add these two functions after `build_context` (do NOT remove existing code). Add `from rag_types import RetrievedContext` to the imports at the top:
```python
def build_context_from_contexts(contexts: list[RetrievedContext]) -> str:
    """Build an evidence block from RetrievedContext objects (corpus or web)."""
    parts = []
    for i, ctx in enumerate(contexts, start=1):
        meta = ctx.metadata or {}
        parts.append(
            f"[Source {i}]\n"
            f"Product: {meta.get('product', meta.get('title', 'N/A'))}\n"
            f"URL: {ctx.url or meta.get('url', 'N/A')}\n\n"
            f"{ctx.text}\n"
        )
    return "\n\n".join(parts)


def generate_answer(query: str, contexts: list[RetrievedContext]) -> str:
    """Generate a grounded answer from pre-retrieved contexts (corpus or web)."""
    context = build_context_from_contexts(contexts)
    prompt = f"""
You are BoostRAG, a BMW M340i aftermarket parts research assistant.

Answer the user's question using only the retrieved evidence below.
Do not invent facts.
If the evidence is insufficient or conflicting, say so clearly.
When possible, mention the product or source supporting the answer.
Keep the answer concise and user-friendly.

User question:
{query}

Retrieved evidence:
{context}
"""
    response = client.responses.create(model=GEN_MODEL, input=prompt)
    return response.output_text.strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_generate_answer.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add boostrag-api/answer.py boostrag-api/tests/test_generate_answer.py
git commit -m "feat: add generate_answer for pre-retrieved contexts"
```

---

## Task 6: Retrievers (`retrievers.py`)

**Files:**
- Create: `boostrag-api/retrievers.py`
- Test: `boostrag-api/tests/test_retrievers.py`

**Interfaces:**
- Consumes: `retrieve_chunks` (retrieve.py), `tavily_research_search` (research_search.py), `RetrievedContext`.
- Produces:
  - `CorpusRetriever().retrieve(query, top_k=3) -> list[RetrievedContext]` (origin="corpus")
  - `WebRetriever().retrieve(query, max_results=5) -> list[RetrievedContext]` (origin="web")

- [ ] **Step 1: Write the failing test**

Create `boostrag-api/tests/test_retrievers.py`:
```python
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_corpus_retriever_maps_chunks_to_contexts():
    import retrievers
    fake_chunks = [{"id": "1", "text": "body", "distance": 0.4,
                    "metadata": {"url": "https://x/ES1/", "product": "P"}}]
    with patch.object(retrievers, "retrieve_chunks", return_value=fake_chunks):
        out = retrievers.CorpusRetriever().retrieve("q", top_k=1)
    assert len(out) == 1
    assert out[0].origin == "corpus"
    assert out[0].distance == 0.4
    assert out[0].url == "https://x/ES1/"


def test_web_retriever_maps_research_sources_to_contexts():
    import retrievers
    from research_search import ResearchSource
    fake = [ResearchSource(title="T", url="https://x/ES1/", content="web body",
                           score=11, trust_label="strong_candidate", reason="r")]
    with patch.object(retrievers, "tavily_research_search", return_value=fake):
        out = retrievers.WebRetriever().retrieve("q")
    assert out[0].origin == "web"
    assert out[0].trust_score == 11
    assert out[0].metadata["trust_tier"] == "strong_candidate"
    assert out[0].text == "web body"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_retrievers.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'retrievers'`.

- [ ] **Step 3: Implement**

Create `boostrag-api/retrievers.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_retrievers.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add boostrag-api/retrievers.py boostrag-api/tests/test_retrievers.py
git commit -m "feat: add corpus and web retrievers with shared contract"
```

---

## Task 7: Answer cache (`answer_cache.py`)

**Files:**
- Create: `boostrag-api/answer_cache.py`
- Test: `boostrag-api/tests/test_answer_cache.py`

**Interfaces:**
- Produces:
  - `get_cached(query: str) -> dict | None`
  - `set_cached(query: str, result: dict) -> None`
  - Module constant `CACHE_PATH: Path` (monkeypatchable in tests).

- [ ] **Step 1: Write the failing test**

Create `boostrag-api/tests/test_answer_cache.py`:
```python
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_set_then_get_roundtrip(tmp_path, monkeypatch):
    import answer_cache
    monkeypatch.setattr(answer_cache, "CACHE_PATH", tmp_path / "answers.json")
    answer_cache.set_cached("Best Downpipe?", {"answer": "VRSF", "origin": "web"})
    # normalization: different case/spacing hits the same entry
    got = answer_cache.get_cached("best   downpipe?")
    assert got["answer"] == "VRSF"


def test_miss_returns_none(tmp_path, monkeypatch):
    import answer_cache
    monkeypatch.setattr(answer_cache, "CACHE_PATH", tmp_path / "answers.json")
    assert answer_cache.get_cached("nothing here") is None


def test_expired_entry_is_ignored(tmp_path, monkeypatch):
    import answer_cache
    monkeypatch.setattr(answer_cache, "CACHE_PATH", tmp_path / "answers.json")
    monkeypatch.setenv("CACHE_TTL_HOURS", "0")  # everything immediately stale
    answer_cache.set_cached("q", {"answer": "a"})
    time.sleep(0.01)
    assert answer_cache.get_cached("q") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_answer_cache.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'answer_cache'`.

- [ ] **Step 3: Implement**

Create `boostrag-api/answer_cache.py`:
```python
from __future__ import annotations

import json
import os
import time
from pathlib import Path

CACHE_PATH = Path("data/cache/answers.json")


def _normalize(query: str) -> str:
    return " ".join(query.lower().split())


def _load() -> dict:
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def get_cached(query: str) -> dict | None:
    ttl_seconds = float(os.getenv("CACHE_TTL_HOURS", "24")) * 3600
    entry = _load().get(_normalize(query))
    if not entry:
        return None
    if time.time() - entry["ts"] > ttl_seconds:
        return None
    return entry["result"]


def set_cached(query: str, result: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = _load()
    data[_normalize(query)] = {"ts": time.time(), "result": result}
    CACHE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_answer_cache.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add boostrag-api/answer_cache.py boostrag-api/tests/test_answer_cache.py
git commit -m "feat: add TTL answer cache"
```

---

## Task 8: Provenance kwarg on `ingest_url`

**Files:**
- Modify: `boostrag-api/ingest_urls.py:325-396` (`ingest_url` signature + metadata dict)
- Test: `boostrag-api/tests/test_ingest_provenance.py`

**Interfaces:**
- Produces: `ingest_url(url, *, fitment=None, price_override=None, prefetched_html=None, provenance=None)` — when `provenance` is a dict, its keys are merged into the written metadata JSON.

- [ ] **Step 1: Write the failing test**

Create `boostrag-api/tests/test_ingest_provenance.py`:
```python
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_provenance_fields_written_to_metadata(tmp_path, monkeypatch):
    import ingest_urls
    # redirect all output dirs into tmp_path
    monkeypatch.setattr(ingest_urls, "CLEANED_DIR", tmp_path / "cleaned")
    monkeypatch.setattr(ingest_urls, "LIMITED_DIR", tmp_path / "limited")
    monkeypatch.setattr(ingest_urls, "QUARANTINE_DIR", tmp_path / "quarantine")
    monkeypatch.setattr(ingest_urls, "METADATA_DIR", tmp_path / "metadata")

    body = "BMW M340i B58 VRSF catted downpipe. " * 30  # > 300 chars
    html = f"<html><head><title>VRSF Downpipe</title></head><body><h1>VRSF Downpipe</h1><main>{body}</main></body></html>"

    _, json_path, metadata = ingest_urls.ingest_url(
        "https://www.ecstuning.com/ES1/",
        prefetched_html=html,
        provenance={"origin": "live", "trigger_query": "downpipe", "trust_score": 11},
    )
    on_disk = json.loads(Path(json_path).read_text(encoding="utf-8"))
    assert on_disk["origin"] == "live"
    assert on_disk["trigger_query"] == "downpipe"
    assert on_disk["trust_score"] == 11
    assert metadata["origin"] == "live"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_ingest_provenance.py -v`
Expected: FAIL with `TypeError: ingest_url() got an unexpected keyword argument 'provenance'`.

- [ ] **Step 3: Implement**

In `ingest_urls.py`, change the `ingest_url` signature to add `provenance`:
```python
def ingest_url(
    url: str,
    *,
    fitment: list[str] | None = None,
    price_override: str | None = None,
    prefetched_html: str | None = None,
    provenance: dict | None = None,
) -> tuple[Path, Path, dict]:
```
Then in the `metadata = { ... }` dict, add the provenance merge right before `"text_file": str(txt_path),`:
```python
        **(provenance or {}),
        "text_file": str(txt_path),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_ingest_provenance.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add boostrag-api/ingest_urls.py boostrag-api/tests/test_ingest_provenance.py
git commit -m "feat: support provenance metadata in ingest_url"
```

---

## Task 9: Provenance module — blacklist, log, daily counter, auto-ingest (`provenance.py`)

**Files:**
- Create: `boostrag-api/provenance.py`
- Test: `boostrag-api/tests/test_provenance.py`

**Interfaces:**
- Consumes: `RetrievedContext` (Task 3), `ingest_url` (Task 8).
- Produces:
  - `is_blacklisted(url: str) -> bool`
  - `add_to_blacklist(url: str) -> None`
  - `log_answer(query: str, origin: str, answer: str, sources: list[dict]) -> None`
  - `web_searches_today() -> int`
  - `increment_web_search() -> None`
  - `maybe_ingest_web_sources(query: str, contexts: list[RetrievedContext]) -> list[dict]` (returns per-source `{url, score, ingested}` records)
  - Module path constants `BLACKLIST_PATH`, `QUERIES_LOG`, `COUNTER_PATH` (monkeypatchable).

- [ ] **Step 1: Write the failing test**

Create `boostrag-api/tests/test_provenance.py`:
```python
import json
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_types import RetrievedContext


def _wire(tmp_path, monkeypatch):
    import provenance
    monkeypatch.setattr(provenance, "BLACKLIST_PATH", tmp_path / "blacklist.json")
    monkeypatch.setattr(provenance, "QUERIES_LOG", tmp_path / "queries.jsonl")
    monkeypatch.setattr(provenance, "COUNTER_PATH", tmp_path / "counter.json")
    return provenance


def test_blacklist_add_and_check(tmp_path, monkeypatch):
    p = _wire(tmp_path, monkeypatch)
    assert p.is_blacklisted("https://bad.com/x") is False
    p.add_to_blacklist("https://bad.com/x")
    assert p.is_blacklisted("https://bad.com/x") is True
    # domain-level match
    assert p.is_blacklisted("https://bad.com/other") is True


def test_log_answer_appends_jsonl(tmp_path, monkeypatch):
    p = _wire(tmp_path, monkeypatch)
    p.log_answer("q1", "web", "ans", [{"url": "u", "score": 9, "ingested": True}])
    p.log_answer("q2", "corpus", "ans2", [])
    lines = (tmp_path / "queries.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["query"] == "q1"


def test_daily_counter_increments(tmp_path, monkeypatch):
    p = _wire(tmp_path, monkeypatch)
    assert p.web_searches_today() == 0
    p.increment_web_search()
    p.increment_web_search()
    assert p.web_searches_today() == 2


def test_maybe_ingest_respects_trust_gate_and_blacklist(tmp_path, monkeypatch):
    p = _wire(tmp_path, monkeypatch)
    monkeypatch.setenv("AUTO_INGEST_MIN_SCORE", "9")
    p.add_to_blacklist("https://banned.com/x")
    contexts = [
        RetrievedContext(text="strong", metadata={"title": "A"}, origin="web",
                         trust_score=11, url="https://good.com/a"),
        RetrievedContext(text="weak", metadata={"title": "B"}, origin="web",
                         trust_score=3, url="https://weak.com/b"),
        RetrievedContext(text="banned", metadata={"title": "C"}, origin="web",
                         trust_score=11, url="https://banned.com/x"),
    ]
    with patch.object(p, "ingest_url") as mock_ingest:
        mock_ingest.return_value = (Path("t.txt"), Path("t.json"), {})
        records = p.maybe_ingest_web_sources("q", contexts)
    # only the good, high-score, non-blacklisted source is ingested
    assert mock_ingest.call_count == 1
    ingested = [r for r in records if r["ingested"]]
    assert len(ingested) == 1 and ingested[0]["url"] == "https://good.com/a"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_provenance.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'provenance'`.

- [ ] **Step 3: Implement**

Create `boostrag-api/provenance.py`:
```python
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
    if url not in data["urls"]:
        data["urls"].append(url)
    dom = _domain(url)
    if dom not in data["domains"]:
        data["domains"].append(dom)
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
        if url and score >= min_score and not is_blacklisted(url):
            title = ctx.metadata.get("title", "Live Web Source")
            try:
                ingest_url(
                    url,
                    prefetched_html=_text_to_html(title, ctx.text),
                    provenance={
                        "origin": "live",
                        "trigger_query": query,
                        "trust_score": score,
                        "ingested_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                ingested = True
            except Exception:
                ingested = False  # thin/blocked content — best-effort, never raises
        records.append({"url": url, "score": score, "ingested": ingested})
    return records
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_provenance.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add boostrag-api/provenance.py boostrag-api/tests/test_provenance.py
git commit -m "feat: add provenance log, blacklist, daily counter, auto-ingest"
```

---

## Task 10: Orchestrator (`orchestrator.py`)

**Files:**
- Create: `boostrag-api/orchestrator.py`
- Test: `boostrag-api/tests/test_orchestrator.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `answer_question(query: str, top_k: int = 3) -> AnswerResult`.

**Behavior:**
1. Return cached result if present (as `AnswerResult`).
2. Corpus retrieve → assess confidence.
3. If sufficient → generate from corpus, `origin="corpus"`.
4. Else, if `web_searches_today() < DAILY_WEB_SEARCH_CAP` → `increment_web_search()`, web retrieve; if any web contexts → generate, `origin="web"`, then `maybe_ingest_web_sources`.
5. Else (fuse tripped or no web results): if corpus had anything, answer from it `origin="corpus"`; else `origin="none"` with a fixed message.
6. Always `log_answer(...)`; cache non-empty results.

- [ ] **Step 1: Write the failing test**

Create `boostrag-api/tests/test_orchestrator.py`:
```python
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_types import RetrievedContext, Verdict


def _patch_common(orch, monkeypatch, tmp_path):
    # isolate cache + provenance side effects
    import answer_cache, provenance
    monkeypatch.setattr(answer_cache, "CACHE_PATH", tmp_path / "c.json")
    monkeypatch.setattr(provenance, "QUERIES_LOG", tmp_path / "q.jsonl")
    monkeypatch.setattr(provenance, "COUNTER_PATH", tmp_path / "n.json")
    monkeypatch.setattr(provenance, "BLACKLIST_PATH", tmp_path / "b.json")


def test_corpus_path_when_confident(tmp_path, monkeypatch):
    import orchestrator
    _patch_common(orchestrator, monkeypatch, tmp_path)
    corpus_ctx = [RetrievedContext(text="body", metadata={"product": "P", "url": "u"},
                                   origin="corpus", distance=0.3)]
    with patch.object(orchestrator.CorpusRetriever, "retrieve", return_value=corpus_ctx), \
         patch.object(orchestrator, "assess_corpus_confidence",
                      return_value=Verdict(True, 0.3, 1)), \
         patch.object(orchestrator, "generate_answer", return_value="corpus answer") as gen, \
         patch.object(orchestrator.WebRetriever, "retrieve") as web:
        result = orchestrator.answer_question("q")
    assert result.origin == "corpus"
    assert result.answer == "corpus answer"
    web.assert_not_called()


def test_web_fallback_when_corpus_weak(tmp_path, monkeypatch):
    import orchestrator
    _patch_common(orchestrator, monkeypatch, tmp_path)
    monkeypatch.setenv("DAILY_WEB_SEARCH_CAP", "15")
    web_ctx = [RetrievedContext(text="web body", metadata={"title": "T", "url": "wu"},
                                origin="web", trust_score=11, url="wu")]
    with patch.object(orchestrator.CorpusRetriever, "retrieve", return_value=[]), \
         patch.object(orchestrator, "assess_corpus_confidence",
                      return_value=Verdict(False, None, 0)), \
         patch.object(orchestrator.WebRetriever, "retrieve", return_value=web_ctx), \
         patch.object(orchestrator, "generate_answer", return_value="web answer"), \
         patch.object(orchestrator, "maybe_ingest_web_sources",
                      return_value=[{"url": "wu", "score": 11, "ingested": True}]) as ing:
        result = orchestrator.answer_question("q")
    assert result.origin == "web"
    ing.assert_called_once()


def test_daily_fuse_blocks_web(tmp_path, monkeypatch):
    import orchestrator, provenance
    _patch_common(orchestrator, monkeypatch, tmp_path)
    monkeypatch.setenv("DAILY_WEB_SEARCH_CAP", "0")  # fuse already blown
    with patch.object(orchestrator.CorpusRetriever, "retrieve", return_value=[]), \
         patch.object(orchestrator, "assess_corpus_confidence",
                      return_value=Verdict(False, None, 0)), \
         patch.object(orchestrator.WebRetriever, "retrieve") as web:
        result = orchestrator.answer_question("q")
    web.assert_not_called()
    assert result.origin == "none"


def test_cache_short_circuits(tmp_path, monkeypatch):
    import orchestrator, answer_cache
    _patch_common(orchestrator, monkeypatch, tmp_path)
    answer_cache.set_cached("q", {"answer": "cached", "origin": "web",
                                  "sources": [], "confidence": {}})
    with patch.object(orchestrator.CorpusRetriever, "retrieve") as corpus:
        result = orchestrator.answer_question("q")
    corpus.assert_not_called()
    assert result.answer == "cached"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_orchestrator.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'orchestrator'`.

- [ ] **Step 3: Implement**

Create `boostrag-api/orchestrator.py`:
```python
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
        answer = generate_answer(query, corpus_ctx)
        sources = _sources_from_contexts(corpus_ctx)
        log_answer(query, "corpus", answer, sources)
        result = AnswerResult(answer, "corpus", sources, confidence)
        set_cached(query, result.__dict__)
        return result

    # Corpus weak -> try web if the daily fuse allows it.
    cap = int(os.getenv("DAILY_WEB_SEARCH_CAP", "15"))
    if web_searches_today() < cap:
        increment_web_search()
        web_ctx = WebRetriever().retrieve(query)
        if web_ctx:
            answer = generate_answer(query, web_ctx)
            sources = _sources_from_contexts(web_ctx)
            ingest_records = maybe_ingest_web_sources(query, web_ctx)
            for s, rec in zip(sources, ingest_records):
                s["ingested"] = rec["ingested"]
            log_answer(query, "web", answer, sources)
            result = AnswerResult(answer, "web", sources, confidence)
            set_cached(query, result.__dict__)
            return result

    # Fuse tripped or no web results -> best corpus answer, else honest none.
    if corpus_ctx:
        answer = generate_answer(query, corpus_ctx)
        sources = _sources_from_contexts(corpus_ctx)
        log_answer(query, "corpus", answer, sources)
        result = AnswerResult(answer, "corpus", sources, confidence)
        set_cached(query, result.__dict__)
        return result

    log_answer(query, "none", NO_ANSWER, [])
    return AnswerResult(NO_ANSWER, "none", [], confidence)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_orchestrator.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add boostrag-api/orchestrator.py boostrag-api/tests/test_orchestrator.py
git commit -m "feat: add hybrid retrieval orchestrator"
```

---

## Task 11: Wire orchestrator into the API (`main.py`)

**Files:**
- Modify: `boostrag-api/main.py` (imports, `Source`/`AskResponse` models, `/ask` body)
- Test: `boostrag-api/tests/test_api_ask.py`

**Interfaces:**
- Consumes: `answer_question` (Task 10).
- Produces: `/ask` returns `{answer, origin, confidence, sources[]}` where each source has `origin`, `trust_tier`.

- [ ] **Step 1: Ensure the test client dep is available**

Run: `./.venv/Scripts/python.exe -c "import httpx"`
If it errors, run: `./.venv/Scripts/python.exe -m pip install httpx`
Expected: no output (import succeeds).

- [ ] **Step 2: Write the failing test**

Create `boostrag-api/tests/test_api_ask.py`:
```python
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from rag_types import AnswerResult


def _client():
    with patch("main.ensure_chroma_collection"):
        import main
        return TestClient(main.app)


def test_ask_returns_origin_and_sources():
    result = AnswerResult(
        answer="web answer", origin="web",
        sources=[{"product": "VRSF", "url": "u", "origin": "web",
                  "trust_tier": "strong_candidate", "price": None, "text_preview": "..."}],
        confidence={"sufficient": False, "nearest_distance": None},
    )
    with patch("main.answer_question", return_value=result):
        resp = _client().post("/ask", json={"query": "downpipe?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["origin"] == "web"
    assert body["sources"][0]["trust_tier"] == "strong_candidate"


def test_ask_rejects_empty_query():
    resp = _client().post("/ask", json={"query": "   "})
    assert resp.status_code == 400
```

- [ ] **Step 3: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_api_ask.py -v`
Expected: FAIL (response has no `origin`; `main` still imports `answer_query`).

- [ ] **Step 4: Implement**

In `main.py`: replace `from answer import answer_query` with `from orchestrator import answer_question`. Update the models and handler:
```python
class Source(BaseModel):
    source_file: str | None = None
    product: str | None = None
    category: str | None = None
    brand: str | None = None
    url: str | None = None
    price: str | None = None
    origin: str | None = None
    trust_tier: str | None = None
    text_preview: str | None = None


class AskResponse(BaseModel):
    answer: str
    origin: str
    confidence: dict = {}
    sources: list[Source]
```
Replace the body of `ask_boostrag` after the empty-query check with:
```python
    try:
        result = answer_question(query=query, top_k=request.top_k)
        sources = [Source(**s) for s in result.sources]
        return AskResponse(
            answer=result.answer,
            origin=result.origin,
            confidence=result.confidence,
            sources=sources,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"BoostRAG failed to answer the query: {exc}",
        ) from exc
```
Note: `Source(**s)` ignores no extra keys, so ensure `_sources_from_contexts` only emits fields declared on `Source`. It does (product, url, origin, trust_tier, price, text_preview). The `ingested` key added in the orchestrator is on the logged dict, not the returned `sources` — remove it before returning by having `Source(**{k: v for k, v in s.items() if k in Source.model_fields})`.

Use this exact source-building line in the handler:
```python
        sources = [Source(**{k: v for k, v in s.items() if k in Source.model_fields}) for s in result.sources]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_api_ask.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add boostrag-api/main.py boostrag-api/tests/test_api_ask.py
git commit -m "feat: serve hybrid answers with origin and trust labels from /ask"
```

---

## Task 12: Purge CLI (`purge_source.py`)

**Files:**
- Create: `boostrag-api/purge_source.py`
- Test: `boostrag-api/tests/test_purge_source.py`

**Interfaces:**
- Consumes: `add_to_blacklist` (Task 9).
- Produces: `purge_source(url: str, *, collection=None) -> dict` returning `{blacklisted, chunks_deleted, files_deleted}`; plus a `__main__` CLI (`python purge_source.py <url>`).

- [ ] **Step 1: Write the failing test**

Create `boostrag-api/tests/test_purge_source.py`:
```python
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_purge_blacklists_and_deletes_files(tmp_path, monkeypatch):
    import purge_source, provenance, ingest_urls
    monkeypatch.setattr(provenance, "BLACKLIST_PATH", tmp_path / "blacklist.json")
    monkeypatch.setattr(purge_source, "METADATA_DIR", tmp_path / "metadata")
    (tmp_path / "metadata").mkdir()
    # a metadata file whose url matches -> should be deleted along with its text file
    txt = tmp_path / "vrsf.txt"; txt.write_text("body", encoding="utf-8")
    meta = tmp_path / "metadata" / "vrsf.json"
    meta.write_text(json.dumps({"url": "https://bad.com/ES1/", "text_file": str(txt)}), encoding="utf-8")

    fake_collection = MagicMock()
    result = purge_source.purge_source("https://bad.com/ES1/", collection=fake_collection)

    assert result["blacklisted"] is True
    assert result["files_deleted"] >= 1
    assert not txt.exists() and not meta.exists()
    fake_collection.delete.assert_called_once()  # chunks removed by url metadata
    assert provenance.is_blacklisted("https://bad.com/ES1/")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_purge_source.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'purge_source'`.

- [ ] **Step 3: Implement**

Create `boostrag-api/purge_source.py`:
```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

import chromadb

from provenance import add_to_blacklist
from retrieve import CHROMA_PATH, COLLECTION_NAME

METADATA_DIR = Path("data/metadata")


def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_collection(name=COLLECTION_NAME)


def purge_source(url: str, *, collection=None) -> dict:
    """Remove a source's chunks + files and blacklist it so it can't be re-ingested."""
    if collection is None:
        collection = _get_collection()

    # 1. delete chunks whose metadata url matches
    collection.delete(where={"url": url})

    # 2. delete cleaned text + metadata files that reference this url
    files_deleted = 0
    for meta_path in METADATA_DIR.glob("*.json"):
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("url") == url:
            text_file = data.get("text_file")
            if text_file and Path(text_file).exists():
                Path(text_file).unlink()
                files_deleted += 1
            meta_path.unlink()
            files_deleted += 1

    # 3. blacklist
    add_to_blacklist(url)

    return {"blacklisted": True, "chunks_deleted": True, "files_deleted": files_deleted}


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge and blacklist a bad source URL.")
    parser.add_argument("url", help="The source URL to purge and ban.")
    args = parser.parse_args()
    result = purge_source(args.url)
    print(f"Purged {args.url}: {result}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_purge_source.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add boostrag-api/purge_source.py boostrag-api/tests/test_purge_source.py
git commit -m "feat: add purge_source CLI to remove and blacklist bad sources"
```

---

## Task 13: Frontend — origin badge, trust chips, none-state (`App.jsx`)

**Files:**
- Modify: `boostrag-frontend/src/App.jsx` (the `SourceBackedAnswers` component and wherever the `/ask` response is consumed)

**Interfaces:**
- Consumes: `/ask` response `{answer, origin, confidence, sources[{origin, trust_tier, product, url, price, text_preview}]}`.

- [ ] **Step 1: Locate the answer-rendering component**

Run: `grep -n "SourceBackedAnswers\|origin\|sources" boostrag-frontend/src/App.jsx`
Read that component to see how `answer` and `sources` are currently rendered.

- [ ] **Step 2: Add the origin badge**

At the top of the rendered answer (inside `SourceBackedAnswers`, above the `react-markdown` block), add a badge driven by `origin`:
```jsx
{origin && (
  <span
    className={
      "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium mb-2 " +
      (origin === "corpus"
        ? "bg-green-500/15 text-green-400"
        : origin === "web"
        ? "bg-blue-500/15 text-blue-400"
        : "bg-neutral-500/15 text-neutral-400")
    }
  >
    {origin === "corpus"
      ? "● From your trusted corpus"
      : origin === "web"
      ? "● Live web research — less vetted"
      : "● No confident answer yet"}
  </span>
)}
```
Make sure `origin` is destructured/passed from the API response into this component.

- [ ] **Step 3: Add trust-tier chips to source cards**

On each source card, where product/url render, add (guard for missing `trust_tier`):
```jsx
{src.trust_tier && (
  <span className="ml-2 rounded bg-neutral-700/50 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-neutral-300">
    {src.trust_tier}
  </span>
)}
```

- [ ] **Step 4: Handle the `none` state**

Where the answer body renders, when `origin === "none"` (or `answer` equals the no-answer message), show the honest empty state instead of source cards:
```jsx
{origin === "none" ? (
  <p className="text-neutral-400 italic">
    BoostRAG doesn't have a confident answer for this yet.
  </p>
) : (
  /* existing answer + sources rendering */
)}
```

- [ ] **Step 5: Manually verify in the browser**

Run backend: `cd boostrag-api && ./.venv/Scripts/python.exe -m uvicorn main:app --reload`
Run frontend: `cd boostrag-frontend && npm run dev`
Ask a question clearly IN the corpus → green "trusted corpus" badge. Ask something clearly outside it → blue "live web research" badge and web source cards with trust chips.

- [ ] **Step 6: Commit**

```bash
git add boostrag-frontend/src/App.jsx
git commit -m "feat: show answer origin badge and source trust tiers in UI"
```

---

## Task 14: Calibrate `MAX_DISTANCE` (manual)

**Files:**
- Modify: `boostrag-api/.env` (add tuned `MAX_DISTANCE`)
- Reference: `boostrag-api/.env.example` (document the knob)

- [ ] **Step 1: Add a scratch calibration script**

Create `boostrag-api/scratch_calibrate.py` (not committed):
```python
from retrieve import retrieve_chunks

IN_CORPUS = ["best downpipe for M340i", "VRSF charge pipe B58", "cooling upgrade M340i"]
OUT_OF_CORPUS = ["how to tune a Subaru WRX", "best tires for a Honda Civic", "Tesla Model 3 brakes"]

for label, qs in [("IN", IN_CORPUS), ("OUT", OUT_OF_CORPUS)]:
    for q in qs:
        chunks = retrieve_chunks(q, top_k=3)
        nearest = min((c["distance"] for c in chunks), default=None)
        print(f"{label:4} nearest={nearest}  q={q}")
```

- [ ] **Step 2: Run it and read the split**

Run: `cd boostrag-api && ./.venv/Scripts/python.exe scratch_calibrate.py`
Expected: IN-corpus nearest distances cluster low; OUT-of-corpus cluster high. Pick `MAX_DISTANCE` between the two clusters.

- [ ] **Step 3: Set the tuned value**

Add to `boostrag-api/.env`: `MAX_DISTANCE=<chosen value>`.
Add a documented line to `boostrag-api/.env.example`: `# MAX_DISTANCE=1.0  # corpus 'good enough' cutoff; tune per calibration`.

- [ ] **Step 4: Delete the scratch script**

Run: `rm boostrag-api/scratch_calibrate.py`

- [ ] **Step 5: Commit**

```bash
git add boostrag-api/.env.example
git commit -m "docs: document MAX_DISTANCE calibration knob"
```

---

## Task 15: Full-suite green + env documentation

**Files:**
- Modify: `boostrag-api/.env.example`

- [ ] **Step 1: Run the entire test suite**

Run: `cd boostrag-api && ./.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: all tests PASS, including the original 18 scraper tests.

- [ ] **Step 2: Document all new env knobs in `.env.example`**

Append:
```
# --- Hybrid retrieval knobs (all optional; defaults shown) ---
# MAX_DISTANCE=1.0
# MIN_STRONG_CHUNKS=1
# WEB_QUERY_EXPANSION=2
# DAILY_WEB_SEARCH_CAP=15
# AUTO_INGEST_MIN_SCORE=9
# CACHE_TTL_HOURS=24
```

- [ ] **Step 3: Commit**

```bash
git add boostrag-api/.env.example
git commit -m "docs: document hybrid retrieval env knobs"
```

---

## Self-Review Notes (coverage map)

- Spec §4 orchestrator + B-seam → Tasks 3, 6, 10.
- Spec §5 components / answer.py refactor → Tasks 5, 11.
- Spec §5 research_search bugfix → Task 1.
- Spec §6 API shape → Task 11.
- Spec §7 confidence decision → Task 4 (+ calibration Task 14).
- Spec §8 auto-ingest + provenance + purge/blacklist → Tasks 8, 9, 12.
- Spec §9 error handling + cost levers (expansion cap, cache, daily fuse) → Tasks 2, 7, 9, 10.
- Spec §3 origin labeling in UI → Task 13.
- Spec §10 testing → every task is TDD; Task 15 confirms full suite.
