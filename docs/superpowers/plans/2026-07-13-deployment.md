# Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement **Part A** task-by-task. **Part B** tasks are manual dashboard/runbook steps performed by the user with the controller guiding — not subagent work. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Deploy BoostRAG as a public, reviewer-safe link (Render backend + Vercel frontend) with layered cost protection, while the same code still runs locally via `start-dev.ps1` unchanged.

**Architecture:** All deployment config is environment-driven with local-friendly defaults. Part A adds a shared storage-root helper, a pinned dependency manifest, env-based CORS, per-IP rate limiting (slowapi), a persistent global daily request cap, and an auto-ingest toggle. Part B stands up the hosts.

**Tech Stack:** Python 3.12, FastAPI, ChromaDB, OpenAI, Tavily, slowapi; React/Vite frontend; Render (backend), Vercel (frontend).

## Global Constraints

- Run Python via `./.venv/Scripts/python.exe` from `boostrag-api/`; tests via `./.venv/Scripts/python.exe -m pytest`.
- **Local dev must not regress:** every new setting has a local default; `.\start-dev.ps1` works with NO env vars set. No new *required* env var for local runs.
- All new tests offline (mock OpenAI/Tavily). Do not run live APIs in tests.
- Existing hybrid-retrieval tests must stay green: `pytest tests/ --ignore=tests/test_ecs_scraper.py` (the ecs_scraper suite is red from an unrelated playwright track — ignore it).
- Env values (verbatim defaults): `BOOSTRAG_DATA_DIR=.`, `ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`, `DAILY_ASK_CAP=500`, `RATE_LIMIT=20/minute`, `AUTO_INGEST_ENABLED=true`.
- Commit messages: no "Co-Authored-By" trailer; concise.

---

## File Structure

**New:**
- `boostrag-api/storage.py` — single source of truth for mutable storage paths (derives from `BOOSTRAG_DATA_DIR`).
- `boostrag-api/requirements.txt` — pinned backend dependencies.
- Tests: `test_storage.py`, `test_cors.py`, `test_rate_limit.py`, `test_daily_cap.py`, `test_auto_ingest_flag.py`.

**Modified:**
- `retrieve.py`, `chunk_embed.py`, `ingest_urls.py`, `provenance.py`, `answer_cache.py` — consume `storage.py` paths instead of hardcoding.
- `main.py` — env CORS, slowapi rate limit, daily-cap dependency.
- `provenance.py` — `AUTO_INGEST_ENABLED` gate + ask-counter functions.

---

# PART A — Code Hardening (TDD)

## Task 1: Storage-root helper + path centralization

**Files:**
- Create: `boostrag-api/storage.py`
- Modify: `retrieve.py:14-16`, `chunk_embed.py:16-18`, `ingest_urls.py:17-21`, `provenance.py:26-28`, `answer_cache.py:8`
- Test: `boostrag-api/tests/test_storage.py`

**Interfaces:**
- Produces: `storage.STORAGE_ROOT: Path`, `storage.DATA_DIR: Path`, `storage.CHROMA_PATH: str`, `storage.COLLECTION_NAME: str`.

- [ ] **Step 1: Write the failing test**

Create `boostrag-api/tests/test_storage.py`:
```python
import sys, importlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_defaults_to_repo_relative(monkeypatch):
    monkeypatch.delenv("BOOSTRAG_DATA_DIR", raising=False)
    import storage; importlib.reload(storage)
    assert storage.DATA_DIR == Path("data")
    assert storage.CHROMA_PATH == str(Path("vectorstore") / "chroma_db")
    assert storage.COLLECTION_NAME == "boostrag_docs"


def test_root_override_relocates_paths(monkeypatch, tmp_path):
    monkeypatch.setenv("BOOSTRAG_DATA_DIR", str(tmp_path))
    import storage; importlib.reload(storage)
    assert storage.DATA_DIR == tmp_path / "data"
    assert storage.CHROMA_PATH == str(tmp_path / "vectorstore" / "chroma_db")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_storage.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'storage'`.

- [ ] **Step 3: Create `storage.py`**

```python
from __future__ import annotations

import os
from pathlib import Path

# Root for all mutable storage. Local default preserves the historical repo
# layout (data/ and vectorstore/ under boostrag-api/). In production set
# BOOSTRAG_DATA_DIR to a mounted persistent disk so state survives restarts.
STORAGE_ROOT = Path(os.getenv("BOOSTRAG_DATA_DIR", "."))

DATA_DIR = STORAGE_ROOT / "data"
CHROMA_PATH = str(STORAGE_ROOT / "vectorstore" / "chroma_db")
COLLECTION_NAME = "boostrag_docs"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_storage.py -v`
Expected: PASS.

- [ ] **Step 5: Refactor the 5 hardcoding files to consume `storage.py`**

In `retrieve.py`, replace the lines:
```python
EMBED_MODEL = "text-embedding-3-small"
CHROMA_PATH = "vectorstore/chroma_db"
COLLECTION_NAME = "boostrag_docs"
```
with:
```python
EMBED_MODEL = "text-embedding-3-small"
from storage import CHROMA_PATH, COLLECTION_NAME
```

In `chunk_embed.py`, replace:
```python
CHROMA_PATH = "vectorstore/chroma_db"
COLLECTION_NAME = "boostrag_docs"
```
with:
```python
from storage import CHROMA_PATH, COLLECTION_NAME
```

In `ingest_urls.py`, replace:
```python
DATA_DIR = Path("data")
```
with:
```python
from storage import DATA_DIR
```
(Leave `CLEANED_DIR = DATA_DIR / "cleaned"` etc. as-is — they now derive from the shared `DATA_DIR`.)

In `provenance.py`, replace:
```python
BLACKLIST_PATH = Path("data/blacklist.json")
QUERIES_LOG = Path("data/provenance/queries.jsonl")
COUNTER_PATH = Path("data/provenance/web_search_counter.json")
```
with:
```python
from storage import DATA_DIR

BLACKLIST_PATH = DATA_DIR / "blacklist.json"
QUERIES_LOG = DATA_DIR / "provenance" / "queries.jsonl"
COUNTER_PATH = DATA_DIR / "provenance" / "web_search_counter.json"
```

In `answer_cache.py`, replace:
```python
CACHE_PATH = Path("data/cache/answers.json")
```
with:
```python
from storage import DATA_DIR

CACHE_PATH = DATA_DIR / "cache" / "answers.json"
```

- [ ] **Step 6: Run the full hybrid suite to confirm no regression**

Run: `./.venv/Scripts/python.exe -m pytest tests/ --ignore=tests/test_ecs_scraper.py -q`
Expected: all pass (existing tests monkeypatch the module-level constants, which still exist — they now just derive their defaults from `storage`).

- [ ] **Step 7: Commit**

```bash
git add boostrag-api/storage.py boostrag-api/retrieve.py boostrag-api/chunk_embed.py boostrag-api/ingest_urls.py boostrag-api/provenance.py boostrag-api/answer_cache.py boostrag-api/tests/test_storage.py
git commit -m "feat: centralize mutable storage paths behind BOOSTRAG_DATA_DIR"
```

---

## Task 2: Pinned `requirements.txt`

**Files:**
- Create: `boostrag-api/requirements.txt`

- [ ] **Step 1: Create the file** (pinned to the current venv)

```
fastapi==0.136.1
uvicorn==0.46.0
chromadb==1.5.8
openai==2.33.0
tavily-python==0.7.24
beautifulsoup4==4.14.3
lxml==6.1.0
pydantic==2.13.3
pydantic-settings==2.14.0
python-dotenv==1.2.2
requests==2.33.1
httpx==0.28.1
slowapi==0.1.9
```

- [ ] **Step 2: Verify it installs cleanly into a scratch venv**

Run:
```bash
python -m venv /tmp/deploy-check && /tmp/deploy-check/Scripts/python.exe -m pip install -r boostrag-api/requirements.txt -q && /tmp/deploy-check/Scripts/python.exe -c "import fastapi, uvicorn, chromadb, openai, tavily, bs4, lxml, slowapi; print('all imports OK')"
```
Expected: `all imports OK`. (If `slowapi==0.1.9` is unavailable, use the latest `0.1.x`; record the version you pinned.)

- [ ] **Step 3: Install slowapi into the working venv** (needed by later tasks)

Run: `./.venv/Scripts/python.exe -m pip install slowapi`
Expected: installs without error.

- [ ] **Step 4: Commit**

```bash
git add boostrag-api/requirements.txt
git commit -m "build: add pinned backend requirements.txt with slowapi"
```

---

## Task 3: Env-driven CORS

**Files:**
- Modify: `main.py:16-25`
- Test: `boostrag-api/tests/test_cors.py`

**Interfaces:**
- Consumes: env `ALLOWED_ORIGINS` (comma-separated).

- [ ] **Step 1: Write the failing test**

Create `boostrag-api/tests/test_cors.py`:
```python
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient


def _client():
    with patch("main.ensure_chroma_collection"):
        import importlib, main; importlib.reload(main)
        return TestClient(main.app)


def test_allowed_origin_is_echoed(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://boostrag.vercel.app")
    resp = _client().get("/", headers={"Origin": "https://boostrag.vercel.app"})
    assert resp.headers.get("access-control-allow-origin") == "https://boostrag.vercel.app"


def test_default_allows_localhost(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    resp = _client().get("/", headers={"Origin": "http://localhost:5173"})
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_cors.py -v`
Expected: FAIL — the vercel origin is not echoed (only localhost is hardcoded).

- [ ] **Step 3: Implement**

In `main.py`, add near the top imports: `import os`. Replace the `app.add_middleware(CORSMiddleware, allow_origins=[...], ...)` block with:
```python
_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
_allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_cors.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add boostrag-api/main.py boostrag-api/tests/test_cors.py
git commit -m "feat: configure CORS allowlist from ALLOWED_ORIGINS env"
```

---

## Task 4: Per-IP rate limiting (slowapi)

**Files:**
- Modify: `main.py` (limiter setup + `/ask` signature)
- Test: `boostrag-api/tests/test_rate_limit.py`

**Interfaces:**
- Consumes: env `RATE_LIMIT` (default `20/minute`), read at request time via a callable so tests can set it.
- Produces: `/ask` handler signature now `ask_boostrag(request: Request, payload: AskRequest)`.

- [ ] **Step 1: Write the failing test**

Create `boostrag-api/tests/test_rate_limit.py`:
```python
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from rag_types import AnswerResult


def _client(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT", "2/minute")
    with patch("main.ensure_chroma_collection"):
        # reloading main builds a fresh Limiter with empty in-memory state,
        # isolating rate-limit counts between tests (no shared limiter bleed)
        import importlib, main; importlib.reload(main)
        client = TestClient(main.app)
        return main, client


def test_third_request_in_window_is_rate_limited(monkeypatch):
    main, client = _client(monkeypatch)
    result = AnswerResult(answer="a", origin="corpus", sources=[], confidence={})
    with patch("main.answer_question", return_value=result):
        r1 = client.post("/ask", json={"query": "q"})
        r2 = client.post("/ask", json={"query": "q"})
        r3 = client.post("/ask", json={"query": "q"})
    assert r1.status_code == 200 and r2.status_code == 200
    assert r3.status_code == 429
    assert "slow down" in r3.json()["detail"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rate_limit.py -v`
Expected: FAIL — no rate limiting yet (`main.limiter` doesn't exist).

- [ ] **Step 3: Implement**

In `main.py`, add imports:
```python
from fastapi import FastAPI, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
```
After `app = FastAPI(...)`, add:
```python
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "You're asking a lot, very fast — please slow down and try again in a minute."},
    )
```
Change the `/ask` handler signature and decorate it:
```python
@app.post("/ask", response_model=AskResponse)
@limiter.limit(lambda: os.getenv("RATE_LIMIT", "20/minute"))
def ask_boostrag(request: Request, payload: AskRequest) -> AskResponse:
    query = payload.query.strip()
    ...
```
Update the body to use `payload` instead of `request` for the query and `top_k` (the Starlette `Request` is now `request`; the JSON body is `payload`). Everything else in the handler stays the same.

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rate_limit.py -v`
Expected: PASS.

Then make `tests/test_api_ask.py`'s `_client()` reload `main` for limiter isolation — change its body to:
```python
def _client():
    with patch("main.ensure_chroma_collection"):
        import importlib, main; importlib.reload(main)
        return TestClient(main.app)
```
Run `./.venv/Scripts/python.exe -m pytest tests/test_api_ask.py -v` — the existing API tests must still pass (body still binds to `AskRequest` regardless of param name; reload gives each test a fresh limiter).

- [ ] **Step 5: Commit**

```bash
git add boostrag-api/main.py boostrag-api/tests/test_rate_limit.py boostrag-api/tests/test_api_ask.py
git commit -m "feat: add per-IP rate limiting to /ask via slowapi"
```

---

## Task 5: Persistent global daily request cap

**Files:**
- Modify: `provenance.py` (add ask-counter functions), `main.py` (`/ask` cap check)
- Test: `boostrag-api/tests/test_daily_cap.py`

**Interfaces:**
- Consumes: env `DAILY_ASK_CAP` (default 500).
- Produces: `provenance.asks_today() -> int`, `provenance.increment_ask() -> None` (persist to `DATA_DIR/provenance/ask_counter.json`, module constant `ASK_COUNTER_PATH`).

- [ ] **Step 1: Write the failing test**

Create `boostrag-api/tests/test_daily_cap.py`:
```python
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from rag_types import AnswerResult


def test_over_cap_returns_friendly_notice(monkeypatch, tmp_path):
    monkeypatch.setenv("DAILY_ASK_CAP", "1")
    monkeypatch.setenv("RATE_LIMIT", "100/minute")
    import provenance
    monkeypatch.setattr(provenance, "ASK_COUNTER_PATH", tmp_path / "ask.json")
    with patch("main.ensure_chroma_collection"):
        import importlib, main; importlib.reload(main)
        client = TestClient(main.app)
    result = AnswerResult(answer="a", origin="corpus", sources=[], confidence={})
    with patch("main.answer_question", return_value=result):
        r1 = client.post("/ask", json={"query": "q"})
        r2 = client.post("/ask", json={"query": "q"})
    assert r1.status_code == 200 and r1.json()["origin"] == "corpus"
    assert r2.status_code == 200 and r2.json()["origin"] == "none"
    assert "busy day" in r2.json()["answer"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_daily_cap.py -v`
Expected: FAIL — no cap logic; both requests answer normally.

- [ ] **Step 3: Implement the counter in `provenance.py`**

Add near the other counter constants:
```python
ASK_COUNTER_PATH = DATA_DIR / "provenance" / "ask_counter.json"


def asks_today() -> int:
    data = _load_json(ASK_COUNTER_PATH, {})
    return int(data.get(date.today().isoformat(), 0))


def increment_ask() -> None:
    ASK_COUNTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = _load_json(ASK_COUNTER_PATH, {})
    today = date.today().isoformat()
    data[today] = int(data.get(today, 0)) + 1
    ASK_COUNTER_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
```

- [ ] **Step 4: Implement the cap check in `main.py`**

Add `from provenance import asks_today, increment_ask` and a module constant for the busy message:
```python
BUSY_MESSAGE = "BoostRAG has had a busy day and hit its demo limit. Please check back tomorrow!"
```
In `ask_boostrag`, right after the empty-query check and before calling `answer_question`:
```python
    cap = int(os.getenv("DAILY_ASK_CAP", "500"))
    if asks_today() >= cap:
        return AskResponse(answer=BUSY_MESSAGE, origin="none", confidence={}, sources=[])
    increment_ask()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_daily_cap.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add boostrag-api/provenance.py boostrag-api/main.py boostrag-api/tests/test_daily_cap.py
git commit -m "feat: persistent global daily /ask cap with friendly notice"
```

---

## Task 6: `AUTO_INGEST_ENABLED` toggle

**Files:**
- Modify: `provenance.py` (`maybe_ingest_web_sources`)
- Test: `boostrag-api/tests/test_auto_ingest_flag.py`

**Interfaces:**
- Consumes: env `AUTO_INGEST_ENABLED` (default `true`). When falsey, `maybe_ingest_web_sources` records every source as not ingested and calls no ingestion.

- [ ] **Step 1: Write the failing test**

Create `boostrag-api/tests/test_auto_ingest_flag.py`:
```python
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_types import RetrievedContext


def test_flag_off_skips_ingestion(tmp_path, monkeypatch):
    import provenance
    monkeypatch.setattr(provenance, "BLACKLIST_PATH", tmp_path / "b.json")
    monkeypatch.setenv("AUTO_INGEST_ENABLED", "false")
    monkeypatch.setenv("AUTO_INGEST_MIN_SCORE", "9")
    ctx = [RetrievedContext(text="strong", metadata={"title": "A"}, origin="web",
                            trust_score=11, url="https://good.com/a")]
    with patch.object(provenance, "ingest_url") as mock_ingest:
        records = provenance.maybe_ingest_web_sources("q", ctx)
    mock_ingest.assert_not_called()
    assert records[0]["ingested"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_auto_ingest_flag.py -v`
Expected: FAIL — ingestion still runs (flag not checked).

- [ ] **Step 3: Implement**

In `provenance.py` `maybe_ingest_web_sources`, at the very top of the function body add:
```python
    if os.getenv("AUTO_INGEST_ENABLED", "true").lower() not in ("true", "1", "yes"):
        return [{"url": ctx.url or "", "score": (ctx.trust_score if ctx.trust_score is not None else float("-inf")), "ingested": False, "route": None} for ctx in contexts]
```
(`os` is already imported in provenance.py.)

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_auto_ingest_flag.py tests/test_provenance.py -v`
Expected: all PASS (default-on path unchanged).

- [ ] **Step 5: Commit**

```bash
git add boostrag-api/provenance.py boostrag-api/tests/test_auto_ingest_flag.py
git commit -m "feat: gate auto-ingest behind AUTO_INGEST_ENABLED flag"
```

---

## Task 7: Full-suite green + local regression check

- [ ] **Step 1: Run the whole hybrid suite**

Run: `./.venv/Scripts/python.exe -m pytest tests/ --ignore=tests/test_ecs_scraper.py -q`
Expected: all pass (existing + 5 new test files).

- [ ] **Step 2: Confirm local launch still works with NO deployment env vars**

Run (from repo root, in a separate shell): `.\start-dev.ps1`
Then: `curl -s http://127.0.0.1:8000/` → `{"status":"BoostRAG API is running"}`, and open http://localhost:5173 and run one query. Confirm it answers. (This proves the local-dev-preserved constraint.) Stop the servers when done.

- [ ] **Step 3: Commit any doc updates** (e.g. note new env vars in `.env.example`)

Add the new knobs to `boostrag-api/.env.example`:
```
# --- Deployment knobs (optional; local defaults shown) ---
# BOOSTRAG_DATA_DIR=.
# ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
# DAILY_ASK_CAP=500
# RATE_LIMIT=20/minute
# AUTO_INGEST_ENABLED=true
```
```bash
git add boostrag-api/.env.example
git commit -m "docs: document deployment env knobs"
```

---

# PART B — Deploy Runbook (manual; user performs dashboard steps, controller guides)

> These are not code tasks. The user creates accounts, enters secrets, and clicks deploy; the controller guides and verifies. **Never paste secrets into git or chat.**

## Task 8: Set provider spend caps (the hard floor — do this FIRST)

- [ ] In the **OpenAI dashboard** → Billing → Limits: set a hard **monthly budget cap** (e.g. $5). This is the guarantee against overspend; set it before the link is public.
- [ ] Confirm **Tavily** is on the free tier (inherently capped ~1,000 credits/month).
- [ ] Verify the keys in `boostrag-api/.env` still work locally (`start-dev.ps1` → one query).

## Task 9: Deploy the backend to Render

- [ ] Push all Part A commits to `main` (`git push origin main`).
- [ ] In **Render** → New → Web Service → connect the GitHub repo, root directory `boostrag-api`.
- [ ] Build command: `pip install -r requirements.txt`. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`.
- [ ] Plan: **Starter ($7)**. Add a **persistent disk** (~1 GB) mounted at `/var/data`.
- [ ] Environment variables: `OPENAI_API_KEY`, `TAVILY_API_KEY` (secrets), `BOOSTRAG_DATA_DIR=/var/data`, `ALLOWED_ORIGINS=<vercel-url-from-Task-10>`, `DAILY_ASK_CAP=500`, `RATE_LIMIT=20/minute`, `AUTO_INGEST_ENABLED=true`.
- [ ] Deploy. Watch logs for OOM (see spec §5 risk). When healthy, hit `https://<service>.onrender.com/` → status JSON, and `POST /ask` a test query → confirm a labeled answer. Record the backend URL.

## Task 10: Deploy the frontend to Vercel

- [ ] In **Vercel** → New Project → import the repo, root directory `boostrag-frontend` (framework auto-detected: Vite).
- [ ] Environment variable: `VITE_BOOSTRAG_API_URL=https://<render-backend-url>`.
- [ ] Deploy. Note the assigned `*.vercel.app` URL.
- [ ] Back in **Render**, set `ALLOWED_ORIGINS` to that Vercel URL and redeploy the backend (so CORS allows the frontend).

## Task 11: Live verification (via the `verify` skill)

- [ ] Open the Vercel URL. Run an **in-corpus** query → green "trusted corpus" badge + source cards.
- [ ] Run an **out-of-corpus BMW** query (e.g. oil specs) → blue "Live web research" badge + real answer.
- [ ] From a terminal, fire >20 requests/min at `POST /ask` → confirm graceful `429` with the "slow down" message.
- [ ] Confirm a non-allowlisted origin is blocked by CORS (browser console from a random site, or a curl with a bogus `Origin`).
- [ ] Confirm the OpenAI hard cap is set (Task 8).
- [ ] **Local regression:** run `.\start-dev.ps1` → confirm the localhost app still works identically.
- [ ] Done only when: the public link works end-to-end AND local still launches.

---

## Self-Review (coverage map)

- Spec §3 topology → Tasks 9, 10.
- Spec §4 protection: provider cap → Task 8; per-IP → Task 4; daily cap → Task 5; existing fuse/cache → unchanged.
- Spec §5 backend (requirements, disk, start cmd, auto-ingest on) → Tasks 2, 6, 9.
- Spec §6 frontend → Task 10.
- Spec §7 code changes: storage root → Task 1; CORS → Task 3; rate limit → Task 4; daily cap → Task 5; auto-ingest flag → Task 6; requirements → Task 2.
- Spec §8 local-dev-preserved → Global Constraints + Task 7 Step 2 + Task 11 local regression.
- Spec §9 verification → Task 11.
- Spec §10 env config → Task 7 Step 3 (`.env.example`) + per-task env reads.
