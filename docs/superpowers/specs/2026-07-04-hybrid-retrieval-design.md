# Hybrid Retrieval — Design Spec

**Date:** 2026-07-04
**Status:** Approved (design), pending implementation plan
**Scope:** Retrieval upgrade only. Deployment (hosting, accounts, rate-limiting, billing) is a **separate spec**.

---

## 1. Vision & Problem

BoostRAG answers BMW M340i / B58 aftermarket parts questions. Today it can only answer from a
hand-curated local corpus (ChromaDB). That does not scale: you cannot pre-import every source a
user might ask about.

This upgrade makes BoostRAG **answer questions that aren't in the curated corpus** by falling
through to live web search when the corpus comes up short — with honest source labeling and an
autonomous, auditable feedback loop that grows the corpus over time.

**The pitch this enables:** *"Ask it anything about your BMW build, get a cited answer with trust
tiers, and the system gets smarter and cheaper every time someone uses it."*

## 2. Goals / Non-Goals

**Goals (this spec):**
- Auto-fallback from local corpus to live web search when corpus confidence is low.
- Every answer labeled by origin (trusted corpus vs. live web) with cited, trust-tiered sources.
- Autonomous ingestion of high-trust web sources into the corpus, with full provenance.
- A paper trail (answer → sources) and a one-command purge + blacklist for bad sources.
- Extremely conservative, free-tier-only cost model with a hard daily fuse.
- Clean interfaces so agentic tool-calling (Approach B) can slot in later.

**Non-Goals (deferred):**
- Deployment / hosting, accounts, per-user rate limiting, cost dashboards → **deployment spec**.
- "Was this helpful?" user feedback UI → **v2** (design leaves a hook for it).
- Agentic LLM-driven retrieval (Approach B) → **v2** (interface seam built now).
- Bulk scraper seeding (Playwright/ECS) → **paused**; live web tier covers demo needs.

## 3. Constraints

- **Budget: near-zero.** Student, no funding. Must run inside Tavily free tier (~1,000
  credits/month) + pennies of OpenAI. No path may risk a surprise bill.
- **Models already cheap:** `gpt-5.4-mini` (generation), `text-embedding-3-small` (embeddings).
  A corpus-only answer costs a fraction of a cent; only the web tier (Tavily) has meaningful cost.
- **Stack unchanged:** FastAPI backend + React/Vite frontend + ChromaDB. Flat-file storage in
  `data/` (no new database — YAGNI).

## 4. Architecture (Approach A: deterministic orchestrator; B-later seam)

```
                    ┌─────────────────────────────────────────┐
   POST /ask ─────► │           orchestrator.py                │
   (main.py)        │  answer_question(query, top_k)           │
                    │                                          │
                    │  0. cache lookup (normalized query)      │──► cache (JSON, TTL)
                    │  1. corpus = CorpusRetriever.retrieve()  │──► retrieve.py (ChromaDB)
                    │  2. verdict = assess_confidence(corpus)  │──► confidence.py
                    │  3. sufficient? ─ yes ─► generate ◄───────┼──► answer.py (generate_answer)
                    │            └─ no ─► WebRetriever.retrieve()│──► research_search.py (Tavily)
                    │                     └─► generate           │
                    │  4. after web answer (best-effort):       │
                    │       • auto-ingest good sources ─────────┼──► ingest_urls.py (+provenance)
                    │       • log answer→sources trail ─────────┼──► provenance.py
                    │  5. cache the result                      │
                    └─────────────────────────────────────────┘
```

**The B-later seam:** both retrievers satisfy one contract —
`retrieve(query) -> list[RetrievedContext]`, where `RetrievedContext` is a uniform
`{text, metadata, origin, trust_score}`. The orchestrator only depends on that contract. To add
agentic retrieval later, write an `AgenticRetriever` satisfying the same contract; the orchestrator
and answer generator are untouched.

## 5. Components

### New modules (`boostrag-api/`)
- **`orchestrator.py`** — the brain. `main.py`'s `/ask` calls `answer_question(query, top_k)`
  instead of `answer_query` directly. Owns cache → corpus → confidence → (web) → generate →
  ingest/log flow.
- **`confidence.py`** — `assess_corpus_confidence(contexts) -> Verdict`. Isolated, testable
  "is the corpus answer good enough?" logic.
- **`provenance.py`** — writes the paper trail; performs provenance-tagged auto-ingestion;
  enforces the blacklist + trust gate.
- **`purge_source.py`** — CLI: remove a source's chunks from ChromaDB, delete its files, add it to
  the blacklist.

### Refactors to existing code
- **`answer.py`** — split retrieval from generation. New `generate_answer(query, contexts) -> str`
  takes pre-retrieved contexts so corpus and web contexts flow through the identical grounded
  generator (keeps labeling honest). Existing `answer_query` may remain as a thin wrapper for the
  CLI / backwards-compat.
- **`research_search.py`** — **prerequisite bugfix:** `score_source` uses `score`/`reasons` before
  initialization (lines ~148–152 run before `score = 0` / `reasons = []` at ~156–157). Fix first;
  add regression test. Also cap query expansion via `WEB_QUERY_EXPANSION` (see §9).

### Frontend (`boostrag-frontend/src/App.jsx`)
- Origin **badge** on the answer: 🟢 "From your trusted corpus" vs 🔵 "Live web research — less vetted".
- **Trust-tier chips** on each source card (corpus: `source_ranker` tiers; web: research scorer labels).
- Honest **`none`** state: "I don't have a good answer for this yet" instead of a hallucination.

## 6. Data Flow & API

`/ask` response gains `origin` and per-source fields:
```jsonc
{
  "answer": "...",
  "origin": "corpus" | "web" | "none",
  "confidence": { "sufficient": true, "nearest_distance": 0.31 },
  "sources": [
    { "product": "VRSF Catted Downpipe B58", "url": "https://...",
      "origin": "corpus" | "web", "trust_tier": "Tier 1",
      "price": "$549.00", "text_preview": "..." }
  ]
}
```
Top-level `origin` drives the headline badge; per-source `origin` supports future mixed answers.

## 7. Confidence Decision (the auto-fallback trigger)

**Signal:** ChromaDB returns a **distance** per retrieved chunk (lower = more similar).

**Rule (v1, deliberately simple):**
```
sufficient  ⟺  at least MIN_STRONG_CHUNKS chunks have distance ≤ MAX_DISTANCE
```
- Empty corpus / zero results → insufficient → web.
- `MIN_STRONG_CHUNKS` default 1; `MAX_DISTANCE` calibrated (see below). Both env-configurable.
- **Every decision is logged** (query, distances, verdict, chosen path) for tuning + demo metrics.

**Why not an LLM self-assessment:** costs an extra model call per query and models are
overconfident. The distance number is free, instant, deterministic.

**Calibration task (explicit):** cannot pick `MAX_DISTANCE` from a desk. Once the web tier works,
run ~10–15 representative questions (some in-corpus, some clearly not), read the distance spread,
set the default. User will help test.

## 8. Autonomous Ingestion, Provenance & Purge

After a **web** answer is delivered (never blocks the response), `provenance.py`:
1. **Blacklist check** — skip banned URL/domain.
2. **Trust gate** — ingest only sources scoring ≥ `AUTO_INGEST_MIN_SCORE` (kept high initially).
3. **Provenance-tagged ingest** — reuse `ingest_urls.py`; metadata JSON gains:
   ```jsonc
   { "origin": "live", "trigger_query": "...", "ingested_at": "ISO-8601", "trust_score": 11 }
   ```

> **Deferred visibility (batch re-embed).** `ingest_url` writes the source into `data/cleaned/`
> but does **not** embed it — the read path (ChromaDB) only sees a source after a re-embed. A
> `rebuild_corpus` step (CLI `python chunk_embed.py --rebuild`, run manually or on a schedule)
> re-embeds `data/cleaned/` so auto-ingested sources become retrievable. So the flywheel is
> **batch**, not live: the corpus grows between rebuilds, not within a single request. Also,
> because the numeric research trust score is independent of `source_ranker`'s tier routing, an
> auto-ingest only counts as `ingested: true` when the source actually lands in `cleaned/`
> (the RAG-visible tier); `limited`/`quarantine` placements are logged but not claimed as ingested.

**Paper trail** — every answer (corpus or web) appends one line to `data/provenance/queries.jsonl`:
```jsonc
{"ts":"...","query":"...","origin":"web","answer_preview":"...",
 "sources":[{"url":"...","score":11,"ingested":true}]}
```

**Purge switch** — `python purge_source.py <url>`:
- removes matching chunks from ChromaDB (by `url` metadata),
- deletes `data/cleaned/` + metadata files,
- adds URL/domain to `data/blacklist.json` (barred from future auto-ingest).

**Storage:** flat JSONL + JSON, matching existing `data/` conventions. Inspectable by eye,
trivial to migrate post-funding.

## 9. Error Handling & Cost Model

**Graceful degradation — never a 500 to the user:**
| Failure | Behavior |
|---|---|
| Tavily key missing / API error | log; return best corpus answer, else honest `none` state |
| Web search returns nothing usable | `origin: none`, "no good answer yet" |
| Auto-ingestion fails | log to provenance; answer already delivered (best-effort, non-blocking) |
| Corpus empty (fresh deploy) | every query routes to web automatically |

**Cost levers (all env-configurable):**
1. `WEB_QUERY_EXPANSION=2` — cap the 6-way query expansion in `research_search.py`; ~3–6× less
   Tavily burn.
2. **Answer cache** (`data/cache/answers.json`, TTL) — repeated/demo questions cost $0 after first.
3. `DAILY_WEB_SEARCH_CAP=15` — hard daily fuse; past it, fall back to best corpus answer with a
   quiet "live research paused for today" note. A viral link cannot run up a bill.
4. **Flywheel compounding (batch)** — auto-ingested topics become free corpus hits after the next
   `rebuild_corpus` re-embed (see §8 "Deferred visibility"), not within the same request.

**Realistic bill:** inside Tavily free tier + pennies of OpenAI ≈ **$0–2/month**, with a hard stop.

## 10. Testing (TDD, mirrors existing `tests/`)

- **Unit:** `confidence.py` (sufficient/insufficient/empty); orchestrator routing (mock retrievers →
  corpus vs. web path); `provenance.py` (correct trail, trust gate, blacklist honored);
  `purge_source.py` (removes chunks + blacklists); `score_source` bugfix regression.
- **Integration:** `/ask` corpus-hit → `origin: corpus`; corpus-miss + mocked web → `origin: web` +
  ingestion fired; cache hit → no API calls; daily-fuse-tripped → graceful corpus fallback.
- **No live API calls in tests** — Tavily + OpenAI always mocked; suite is free/offline. Existing 18
  scraper tests stay green.

## 11. Config Summary (env)

| Var | Default | Purpose |
|---|---|---|
| `MAX_DISTANCE` | 1.0 (starting point; calibrate per §7) | corpus "good enough" cutoff |
| `MIN_STRONG_CHUNKS` | 1 | how many close chunks needed |
| `WEB_QUERY_EXPANSION` | 2 | cap Tavily sub-queries per question |
| `DAILY_WEB_SEARCH_CAP` | 15 | hard daily web-search fuse |
| `AUTO_INGEST_MIN_SCORE` | 9 (research scorer "strong_candidate") | trust gate for auto-ingest |
| `CACHE_TTL_HOURS` | 24 | answer cache lifetime |

## 12. Sequencing Recommendations (kept in mind, not built here)

- **Pause the Playwright scraper.** It only grows the local tier and fights Cloudflare; Tavily
  fetches content server-side and sidesteps that wall. Small hand-seeded corpus + live tier is
  enough — and more impressive — for the investor demo. Revisit post-funding.
- **Keep `AUTO_INGEST_MIN_SCORE` high early** to protect the corpus quality moat; loosen once the
  paper trail shows the scoring is trustworthy.
- **Frame the demo around the flywheel + citations,** not "RAG."

## 13. Future Extensions (v2+)

- "Was this helpful?" feedback UI → `flagged` state feeding the same purge/blacklist machinery
  (provenance log already ties answers → sources).
- Agentic tool-calling retriever (Approach B) via the existing retriever contract.
- Bulk corpus seeding (scraper) once volume justifies it.
- Deployment spec: hosting, accounts, per-user/IP rate limiting, cost dashboard.
