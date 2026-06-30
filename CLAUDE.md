# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BoostRAG is a BMW M340i aftermarket parts research assistant. It combines a local RAG pipeline (ChromaDB + OpenAI embeddings) with a FastAPI backend and a React frontend. A secondary live-research layer (Tavily web search) is implemented but not yet wired into the API.

## Repository Layout

```
boostrag-api/       Python FastAPI backend + RAG pipeline
boostrag-frontend/  React + Vite + Tailwind v4 frontend
```

## Commands

### Backend (run from `boostrag-api/`)

```bash
uvicorn main:app --reload          # Start API server on http://127.0.0.1:8000
python chunk_embed.py              # Rebuild the ChromaDB vector store from data/cleaned/
python ingest_urls.py <url>        # Ingest a URL into the corpus (also accepts a .txt file of URLs)
python test_research.py "query"    # Test the Tavily live-search layer (requires TAVILY_API_KEY)
```

### Frontend (run from `boostrag-frontend/`)

```bash
npm run dev     # Start Vite dev server on http://localhost:5173
npm run build   # Production build
npm run lint    # ESLint
```

## Environment

`boostrag-api/.env` (copy from `.env.example`):
```
OPENAI_API_KEY=...
TAVILY_API_KEY=...   # only needed for research_search.py
```

Frontend API base URL is configurable via `VITE_BOOSTRAG_API_URL` (defaults to `http://127.0.0.1:8000`).

## Architecture: Data Flow

**Corpus ingestion (offline):**
1. `ingest_urls.py` — fetches a URL, parses HTML with BeautifulSoup, trust-scores it via `source_ranker.py`, then writes a structured `.txt` to `data/cleaned/` (or `data/limited/` / `data/quarantine/` for lower-trust sources) and JSON metadata to `data/metadata/`.
2. `chunk_embed.py` — reads all `.txt` files from `data/cleaned/` via `preprocess.py`, splits into 1200-char chunks with 200-char overlap, embeds each with OpenAI `text-embedding-3-small`, and upserts into ChromaDB at `vectorstore/chroma_db/` (collection: `boostrag_docs`).

**Query answering (online):**
1. `main.py` → `POST /ask` receives `{query, top_k}`.
2. `retrieve.py` — embeds the query, queries ChromaDB, returns top-k chunks with metadata.
3. `answer.py` — builds a grounded prompt from the chunks and calls OpenAI to generate an answer.
4. Response includes the answer text and deduplicated source metadata (product, brand, category, URL, price, text preview).

The FastAPI startup hook (`ensure_chroma_collection`) auto-builds the vector store from `data/cleaned/` if the ChromaDB collection doesn't exist yet.

## Corpus File Format

Files in `data/cleaned/` follow this structure — `preprocess.py` parses them:

```
Brand: VRSF
Category: Downpipe
Product: VRSF Catted Downpipe B58 M340i
Vehicle: BMW M340i G20
Source Type: product_page
URL: https://...
Price: $499.00

--- body text starts after the blank line ---
```

## Source Trust System (`source_ranker.py`)

Sources are classified into three tiers and routed accordingly:
- **Tier 1 / `cleaned`** — Known high-trust automotive vendors (ECS Tuning, Turner Motorsport, Dinan, etc.)
- **Tier 2 / `limited`** — Community/editorial sources (BimmerPost, Reddit, YouTube)
- **Tier 3 / `quarantine`** — Unknown, thin, or risk-flagged sources

`ingest_urls.py` routes output files based on this classification. Only `data/cleaned/` feeds the RAG pipeline.

## Live Research Layer (`research_search.py`)

`research_search.py` provides Tavily-based live web search with M340i-specific query expansion (expands a user question into up to 6 targeted BMW/B58 search queries) and lightweight source scoring. It is **not yet wired into `main.py`** — it currently exists as a standalone utility testable via `test_research.py`.

Note: `score_source()` in `research_search.py` has a bug — `score` and `reasons` are used before initialization (lines ~148–152 run before the `score = 0` / `reasons = []` lines at ~156–157).

## File Sync Watcher

New files from Claude.ai arrive as `boostrag-update.zip` in `~/Downloads`. A project-agnostic watcher script auto-extracts and routes them:

```
Watcher home: C:\Users\tsmgr\tools\watcher\multi-watch.sh
Archives:     C:\Users\tsmgr\tools\watcher\archive\boostrag\
```

**To start the watcher** (Git Bash, separate terminal, run once per session):
```bash
bash /c/Users/tsmgr/tools/watcher/multi-watch.sh
```

The watcher also handles `jarvis-update.zip` → `C:\Users\tsmgr\Documents\jarvis-agent`. To add a new BoostRAG file route, add a line to `get_dest_boostrag()` inside `multi-watch.sh`.

## Frontend

All UI lives in `boostrag-frontend/src/App.jsx` (single file). Components: `Header`, `SideRail`, `Hero`, `SearchBand`, `Dashboard` (contains `CategoryPanel`, `SourceBackedAnswers`, `TrendingPanel`), `FooterStrip`. Shared primitives: `Panel`, `PanelHeader`, `CornerMarks`.

The dashboard shows static example cards until a query is submitted; after a query, `SourceBackedAnswers` renders the live answer (via `react-markdown`) and source cards. API errors display inline within the same panel.

Tailwind v4 is configured via `@tailwindcss/vite` (no `tailwind.config.js` needed).

## Working Style Preferences

### Token Efficiency

- Skip brainstorming and TDD ceremony for trivial tasks (renames, typo fixes, single-line changes). Just make the change.
- Use the full brainstorming → planning → TDD workflow only for real features.
- Don't re-read files already loaded in context unless they've changed.
- When asked about a specific file, focus there — don't search the whole repo unless necessary.

### Commit Conventions

- Never add "Co-Authored-By: Claude" attribution to commits.
- Keep commit messages concise and descriptive.

### Model Usage

- Default to Sonnet for execution work; switch to Opus only for hard architectural decisions.
- Don't suggest model switches unless genuinely warranted.

### Context Hygiene

- If a session is getting long, suggest `/clear` with a brief summary of what to re-prime.
