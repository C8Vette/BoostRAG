# Deployment — Design Spec

**Date:** 2026-07-13
**Status:** Approved (design), pending implementation plan
**Scope:** Deploy BoostRAG as a public, shareable link (for a Claude fellowship application) while preserving the local `start-dev.ps1` workflow. Retrieval features are already shipped; this spec is hosting + hardening only.

---

## 1. Goal & Context

Produce a **reliable, reviewer-safe public URL** for BoostRAG that a fellowship reviewer can click and use, with **no risk of a surprise API bill**, while the **exact same code still runs locally** from the terminal for on-camera demos.

## 2. Constraints

- **Budget:** near-zero. Chosen tier ≈ **$7.25/mo** (Render Starter $7 + ~$0.25 persistent disk). Frontend is free.
- **No surprise bills — hard requirement.** A widely-shared link must never bill beyond a fixed provider cap.
- **Local dev preserved — hard requirement.** `.\start-dev.ps1` must launch the app locally exactly as it does today, with zero code edits and no new required env vars. All deployment config is env-driven with local-friendly defaults.
- **Upgrade-ready:** free ↔ paid is a dashboard toggle; no code change.
- Same GitHub repo (`main`), auto-deploy on push.

## 3. Architecture / Topology (Approach A: split hosting)

```
   Reviewer browser
        │
        ▼
   Vercel (free, CDN)  ──HTTPS /ask──►  Render (Starter $7, always-on)
   React static build   VITE_BOOSTRAG_    FastAPI + ChromaDB
   boostrag.vercel.app  API_URL           + persistent disk (~$0.25)
                        ◄──JSON answer──   OpenAI + Tavily keys (server-side secrets)
```

- **Frontend → Vercel** (free): `npm run build` (Vite) → static CDN. One env var: `VITE_BOOSTRAG_API_URL` = Render backend URL. Fast regardless of backend state.
- **Backend → Render** (Starter, always-on): `uvicorn main:app --host 0.0.0.0 --port $PORT`. Keys and config as Render env secrets. A small **persistent disk** holds the vector store, corpus, provenance log, blacklist, cache, and counters.

## 4. Cost & Abuse Protection

**One hard guarantee + three throttles in front of it.**

1. **Provider spend caps (the floor — dashboard, no code):** OpenAI hard **monthly usage limit** (e.g. $5) rejects calls when hit; Tavily free tier is inherently capped (~1,000 credits/mo). Worst case: the app stops answering until reset — **it cannot bill beyond the cap.** Existing graceful degradation handles provider errors.
2. **Per-IP rate limit:** `slowapi`, `20/minute` per IP on `/ask`, friendly `429`.
3. **Global daily cap:** `DAILY_ASK_CAP` (default 500) total `/ask` calls/day; past it a polite "busy day" message. On the persistent disk the counter is **properly daily** (survives restarts).
4. **Existing guards:** daily web-search fuse (≤15 Tavily/day) + answer cache (repeat questions = $0) carry over unchanged.

All limit responses render as friendly notices in the UI, not errors.

## 5. Backend Deployment (Render)

- **`requirements.txt`** (new) — pinned to current venv versions: `fastapi==0.136.1`, `uvicorn==0.46.0`, `chromadb==1.5.8`, `openai==2.33.0`, `tavily-python==0.7.24`, `beautifulsoup4`, `lxml`, `pydantic`, `python-dotenv`, `slowapi`.
- **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`.
- **Persistent disk:** mounted (e.g. `/var/data`); the single storage root `BOOSTRAG_DATA_DIR` (see §7.5) points at it, so the vector store, corpus, provenance, blacklist, cache, and counters all live on the disk. Vector store **embeds once and persists** (no repeat cost, fast boots).
- **Corpus on boot:** existing `ensure_chroma_collection` rebuilds from committed `data/cleaned/` only when the collection is absent — a no-op once the disk is warm.
- **Live flywheel ON:** `AUTO_INGEST_ENABLED=true` in prod. Only sources scoring ≥ `AUTO_INGEST_MIN_SCORE` (9) auto-ingest; `purge_source.py` removes bad ones. Persists on disk, so "it got smarter from real use" is demonstrable.
- **Health check:** existing `GET /` serves as Render's health check.

**Known risk (eyes open):** Render Starter is **512 MB RAM**; ChromaDB + deps may be tight. If it OOMs on boot: trim startup imports or step up to the ~$25 tier (2 GB). Verify current plan RAM in the dashboard before assuming.

## 6. Frontend Deployment (Vercel)

Vercel auto-detects Vite. Build → static CDN. Set `VITE_BOOSTRAG_API_URL` to the Render URL in Vercel project settings. Always-on backend means **no cold-start UX needed** — the existing `/ask` loading spinner suffices.

## 7. Code Changes (all backend, all env-driven)

1. **`requirements.txt`** — new, pinned + `slowapi`.
2. **CORS from env** — `main.py` reads `ALLOWED_ORIGINS` (comma-separated); default `http://localhost:5173,http://127.0.0.1:5173`.
3. **Per-IP rate limit** — `slowapi` limiter + `429` handler on `/ask`; rate from env (default `20/minute`).
4. **Global daily cap** — dependency checking a persistent daily counter (reuse provenance counter pattern); `DAILY_ASK_CAP` default 500; friendly over-cap response.
5. **Configurable storage base path** — centralize the storage root (vector store, `data/` for cleaned/provenance/cache/blacklist) behind one env var (e.g. `BOOSTRAG_DATA_DIR`) so prod points at the mounted disk and local defaults to the repo paths. Touches `retrieve.py`, `chunk_embed.py`, `ingest_urls.py`, `provenance.py`, `answer_cache.py` (which currently hardcode paths) — introduce a small shared `storage`/`config` helper rather than editing each in isolation.
6. **`AUTO_INGEST_ENABLED` flag** (default `true`) — clean off-switch; checked in `provenance.maybe_ingest_web_sources`.

## 8. Local Dev Preserved (hard requirement)

- `.\start-dev.ps1` runs unchanged: no env vars set → CORS = localhost, storage = repo-relative `vectorstore/`/`data/`, `AUTO_INGEST_ENABLED=true`, caps at generous defaults, rate limit unobtrusive for a single user.
- **No new *required* env var** for local runs — every new setting has a local default.
- Verification (§9) explicitly re-runs the local `start-dev.ps1` flow to confirm no regression.

## 9. Verification (live, via `verify` skill)

1. Deploy backend → `GET /` healthy → `POST /ask` (in-corpus + out-of-corpus) returns correct labeled answers.
2. Deploy frontend → load the Vercel URL → run green (corpus) and blue (web) paths end-to-end in the real UI.
3. Protection: >20 req/min from one IP → graceful `429`; confirm CORS allows the Vercel origin and blocks others; confirm OpenAI hard cap is set.
4. **Local regression:** run `.\start-dev.ps1` → confirm localhost app still works identically.
5. Only "done" when a real click on the real link works AND local still launches.

## 10. Config Summary (env)

| Var | Local default | Prod (Render/Vercel) | Purpose |
|---|---|---|---|
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Vercel URL | CORS allowlist |
| `BOOSTRAG_DATA_DIR` | repo-relative (`.`) | disk mount (e.g. `/var/data`) | storage root |
| `DAILY_ASK_CAP` | 500 | 500 | global daily `/ask` cap |
| `RATE_LIMIT` | `20/minute` | `20/minute` | per-IP limit |
| `AUTO_INGEST_ENABLED` | `true` | `true` | live flywheel toggle |
| `VITE_BOOSTRAG_API_URL` | `http://127.0.0.1:8000` | Render URL | frontend → backend |
| `OPENAI_API_KEY` / `TAVILY_API_KEY` | `.env` | dashboard secrets | provider keys |

(Existing knobs — `MAX_DISTANCE`, `WEB_QUERY_EXPANSION`, `DAILY_WEB_SEARCH_CAP`, `AUTO_INGEST_MIN_SCORE`, `CACHE_TTL_HOURS` — keep their defaults.)

## 11. Non-Goals / Future

- **Custom domain** — deferred; ships on the free Vercel subdomain.
- **$25 RAM tier** — only if the 512 MB Starter OOMs.
- **Shared rate-limit store (Redis)** — not needed; single always-on instance makes in-memory/on-disk counters sufficient. Would matter only under horizontal scaling.
- **Accounts / auth** — out of scope; the link is open by design for frictionless reviewer access.
