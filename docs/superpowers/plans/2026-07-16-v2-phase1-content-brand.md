# v2 Phase 1 — Content & Brand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Tasks 4 and 8 are verification/merge gates run by the controller (live browser), not subagent work.

**Goal:** Real routed pages for the eight category tabs plus a showroom-grade landing, powered by a new read-only `/browse` endpoint, delivered in two beats that never leave the live site half-styled.

**Architecture:** Evolve the existing Vite+React SPA with `react-router-dom`; decompose the 735-line `App.jsx` into `pages/`, `components/`, `lib/`, `theme/`. Beat 1 = behavior-preserving decomposition + routing + category pages in the current look. Beat 2 = the "showroom upstairs, garage downstairs" redesign + motion. Backend gains one metadata-only endpoint.

**Tech Stack:** React 19, Vite 8, Tailwind v4, framer-motion 12 (already installed — use it for motion + `useReducedMotion`), react-router-dom ^7; FastAPI backend (existing patterns).

## Global Constraints

- **Reviewer-may-click rule:** nothing merges to `main` unless complete + verified (Tasks 4 and 8 are the only merge points).
- Backend: run via `./.venv/Scripts/python.exe` from `boostrag-api/`; tests offline/mocked; suite green with `--ignore=tests/test_ecs_scraper.py`.
- Frontend gate: `npm run lint` (no new errors; 3 pre-existing unrelated errors exist) + `npm run build` succeeds. No frontend unit-test framework — do not add one (YAGNI); the browser pass in Tasks 4/8 is the functional gate.
- **Legal:** no BMW promo assets/trademarks as UI. Imagery from licensed-free commercial-use sources (Unsplash/Pexels) only, each recorded in `boostrag-frontend/ATTRIBUTIONS.md` (photographer + URL). Alt text on all images.
- Design rules: M-accent colors ≤ ~5% of any viewport; every animation gated behind `useReducedMotion()` (framer-motion) or `@media (prefers-reduced-motion: reduce)`.
- $0 hero: high-res licensed still + CSS Ken Burns. No paid stock in this phase.
- Commits: concise, no "Co-Authored-By" trailer.
- `VITE_BOOSTRAG_API_URL` semantics unchanged (default `http://127.0.0.1:8000`).

---

## File Structure (end state)

```
boostrag-api/
  browse.py                    NEW — slug mapping + metadata loader
  main.py                      MODIFIED — GET /browse route
  tests/test_browse.py         NEW

boostrag-frontend/
  vercel.json                  NEW — SPA fallback rewrite
  ATTRIBUTIONS.md              NEW — image credits
  src/
    App.jsx                    SHRINKS to router shell
    lib/api.js                 NEW — askBoostRAG(), browseCategory()
    lib/useAsk.js              NEW — shared ask-state hook
    theme/tokens.js            NEW — zone tokens (Task 5)
    pages/Landing.jsx          NEW
    pages/Research.jsx         NEW
    pages/CategoryPage.jsx     NEW
    components/primitives.jsx  NEW — Panel, PanelHeader, CornerMarks, SmallDot, Sparkline
    components/Header.jsx      Header
    components/SideRail.jsx    SideRail
    components/Hero.jsx        Hero + HeroMiniCard
    components/SearchBand.jsx  SearchBand
    components/Dashboard.jsx   Dashboard + CategoryPanel + TrendingPanel
    components/AnswerPanel.jsx SourceBackedAnswers + OriginBadge
    components/FooterStrip.jsx FooterStrip
```

---

## Task 1: Backend `GET /browse` endpoint

**Files:**
- Create: `boostrag-api/browse.py`
- Modify: `boostrag-api/main.py` (add route)
- Test: `boostrag-api/tests/test_browse.py`

**Interfaces:**
- Produces: `browse.CATEGORY_SLUGS: dict[str, list[str] | None]` (None = all categories), `browse.browse_category(slug: str) -> dict | None` returning `{"category": slug, "count": n, "items": [{product, brand, price, url, trust_tier, text_preview}]}` or `None` for unknown slug. Route `GET /browse?category=<slug>` → 200 with that dict, 404 `{"detail": "Unknown category: <slug>"}` for unknown slugs. Rate-limited like `/ask`; does NOT touch `asks_today`/`increment_ask`.

- [ ] **Step 1: Write the failing test**

Create `boostrag-api/tests/test_browse.py`:
```python
import json
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient


def _write_meta(dirpath, name, **fields):
    dirpath.mkdir(parents=True, exist_ok=True)
    base = {"product": "P", "brand": "B", "price": "$1.00", "url": "https://x/",
            "category": "Intake", "route": "cleaned", "description": "d",
            "title": "T"}
    base.update(fields)
    (dirpath / f"{name}.json").write_text(json.dumps(base), encoding="utf-8")


def test_browse_category_filters_and_shapes(tmp_path, monkeypatch):
    import browse
    monkeypatch.setattr(browse, "METADATA_DIR", tmp_path / "metadata")
    meta = tmp_path / "metadata"
    _write_meta(meta, "a", category="Intake", product="Intake A", trust_tier=1)
    _write_meta(meta, "b", category="Downpipe", product="DP B", trust_tier=1)
    _write_meta(meta, "c", category="Cooling", product="Cool C", trust_tier=1)
    _write_meta(meta, "q", category="Intake", product="Quarantined", route="quarantine")

    result = browse.browse_category("intake-exhaust")
    names = [i["product"] for i in result["items"]]
    assert result["count"] == 2
    assert "Intake A" in names and "DP B" in names
    assert "Cool C" not in names            # wrong category
    assert "Quarantined" not in names       # only cleaned-routed items


def test_browse_overview_returns_all_cleaned(tmp_path, monkeypatch):
    import browse
    monkeypatch.setattr(browse, "METADATA_DIR", tmp_path / "metadata")
    meta = tmp_path / "metadata"
    _write_meta(meta, "a", category="Intake")
    _write_meta(meta, "b", category="Suspension")
    result = browse.browse_category("overview")
    assert result["count"] == 2


def test_browse_unknown_slug_returns_none_and_404(tmp_path, monkeypatch):
    import browse
    monkeypatch.setattr(browse, "METADATA_DIR", tmp_path / "metadata")
    assert browse.browse_category("boats") is None

    with patch("main.ensure_chroma_collection"):
        import importlib, main
        importlib.reload(main)
        client = TestClient(main.app)
    resp = client.get("/browse", params={"category": "boats"})
    assert resp.status_code == 404


def test_browse_route_does_not_consume_daily_ask_cap(tmp_path, monkeypatch):
    import browse, provenance
    monkeypatch.setattr(browse, "METADATA_DIR", tmp_path / "metadata")
    monkeypatch.setattr(provenance, "ASK_COUNTER_PATH", tmp_path / "ask.json")
    _write_meta(tmp_path / "metadata", "a", category="Intake")
    with patch("main.ensure_chroma_collection"):
        import importlib, main
        importlib.reload(main)
        client = TestClient(main.app)
    resp = client.get("/browse", params={"category": "engine"})
    assert resp.status_code == 200
    assert provenance.asks_today() == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_browse.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'browse'`.

- [ ] **Step 3: Create `boostrag-api/browse.py`**

```python
from __future__ import annotations

import json

from storage import DATA_DIR

METADATA_DIR = DATA_DIR / "metadata"

# UI slug -> corpus Category: values. None means "all categories".
CATEGORY_SLUGS: dict[str, list[str] | None] = {
    "overview": None,
    "engine": ["Turbo Inlet", "Tune", "Turbo", "Tuning"],
    "intake-exhaust": ["Intake", "Downpipe", "Charge Pipe", "Exhaust"],
    "cooling": ["Cooling"],
    "suspension": ["Suspension"],
    "wheels-tires": ["Wheels & Tires"],
    "braking": ["Brakes", "Braking"],
    "electronics": ["Electronics"],
}


def browse_category(slug: str) -> dict | None:
    """Return cleaned-routed corpus items for a category slug, or None if unknown."""
    if slug not in CATEGORY_SLUGS:
        return None
    wanted = CATEGORY_SLUGS[slug]

    items: list[dict] = []
    if METADATA_DIR.exists():
        for path in sorted(METADATA_DIR.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if data.get("route") != "cleaned":
                continue
            if wanted is not None and data.get("category") not in wanted:
                continue
            items.append({
                "product": data.get("product") or data.get("title"),
                "brand": data.get("brand"),
                "price": data.get("price"),
                "url": data.get("url"),
                "trust_tier": data.get("trust_tier"),
                "text_preview": (data.get("description") or "")[:250],
            })
    return {"category": slug, "count": len(items), "items": items}
```

- [ ] **Step 4: Add the route to `main.py`**

Add import near the other local imports: `from browse import browse_category`.
Add after the `/ask` handler (same rate limit, no ask-counter):
```python
@app.get("/browse")
@limiter.limit(lambda: os.getenv("RATE_LIMIT", "20/minute"))
def browse(request: Request, category: str) -> dict:
    result = browse_category(category)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Unknown category: {category}")
    return result
```

- [ ] **Step 5: Run tests to verify pass, then the full suite**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_browse.py -v` → all PASS.
Run: `./.venv/Scripts/python.exe -m pytest tests/ --ignore=tests/test_ecs_scraper.py -q` → all pass.

- [ ] **Step 6: Commit**

```bash
git add boostrag-api/browse.py boostrag-api/main.py boostrag-api/tests/test_browse.py
git commit -m "feat: add read-only /browse endpoint for category pages"
```

---

## Task 2: Beat 1 — routing + decomposition (behavior-preserving)

**Files:**
- Modify: `boostrag-frontend/package.json` (add react-router-dom), `boostrag-frontend/src/App.jsx`
- Create: `vercel.json`, `src/lib/api.js`, `src/lib/useAsk.js`, `src/pages/Landing.jsx`, `src/pages/Research.jsx`, and the nine `src/components/*` files per the File Structure table.

**Interfaces:**
- Consumes: nothing new from Task 1 yet.
- Produces: `api.askBoostRAG(query, topK) -> Promise<{answer, origin, confidence, sources}>` (throws Error with friendly message on non-200); `useAsk()` hook returning `{query, setQuery, answer, sources, origin, error, isLoading, submit}`; route shell in `App.jsx`; every component importable from its new file with the SAME name and props as today.

- [ ] **Step 1: Install router**

Run from `boostrag-frontend/`: `npm install react-router-dom`
Expected: added to dependencies (v7.x).

- [ ] **Step 2: Create `vercel.json`** (repo path `boostrag-frontend/vercel.json`)

```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

- [ ] **Step 3: Extract the API layer**

Create `src/lib/api.js` by MOVING the fetch logic currently inside `App()`'s `askBoostRAG` function (App.jsx ~lines 84–130) — same base-URL resolution, same error handling:
```javascript
const API_BASE =
  import.meta.env.VITE_BOOSTRAG_API_URL || "http://127.0.0.1:8000";

export async function askBoostRAG(query, topK = 3) {
  const resp = await fetch(`${API_BASE}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: topK }),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${resp.status})`);
  }
  return resp.json();
}

export async function browseCategory(slug) {
  const resp = await fetch(`${API_BASE}/browse?category=${encodeURIComponent(slug)}`);
  if (!resp.ok) throw new Error(`Browse failed (${resp.status})`);
  return resp.json();
}
```
(Keep the exact request/response field names App.jsx uses today — if the current code reads `data.sources || []` etc., preserve that in the hook below.)

Create `src/lib/useAsk.js` holding the state currently in `App()`:
```javascript
import { useState } from "react";
import { askBoostRAG } from "./api";

export function useAsk(initialQuery = "") {
  const [query, setQuery] = useState(initialQuery);
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [origin, setOrigin] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function submit(q = query) {
    const cleaned = (q || "").trim();
    if (!cleaned) return;
    setIsLoading(true); setError(""); setAnswer(""); setSources([]); setOrigin("");
    try {
      const data = await askBoostRAG(cleaned);
      setAnswer(data.answer);
      setSources(data.sources || []);
      setOrigin(data.origin || "");
      setQuery(cleaned);
    } catch (err) {
      setError(err.message || "Something went wrong reaching BoostRAG.");
    } finally {
      setIsLoading(false);
    }
  }

  return { query, setQuery, answer, sources, origin, error, isLoading, submit };
}
```

- [ ] **Step 4: Move components into their files (mechanical, no behavior change)**

For each component below: cut the function from `App.jsx`, paste into the target file, add needed imports (`react-markdown` etc. — follow what the function references), and `export` it. Named exports except where noted.

| Target file | Functions moved (exact names) |
|---|---|
| `components/primitives.jsx` | `Panel`, `PanelHeader`, `CornerMarks`, `SmallDot`, `Sparkline` |
| `components/Header.jsx` | `Header` |
| `components/SideRail.jsx` | `SideRail` |
| `components/Hero.jsx` | `Hero`, `HeroMiniCard` |
| `components/SearchBand.jsx` | `SearchBand` |
| `components/Dashboard.jsx` | `Dashboard`, `CategoryPanel`, `TrendingPanel` |
| `components/AnswerPanel.jsx` | `SourceBackedAnswers`, `OriginBadge` |
| `components/FooterStrip.jsx` | `FooterStrip` |

Cross-file imports follow usage (e.g. `Dashboard.jsx` imports `SourceBackedAnswers` from `./AnswerPanel` and `Panel`/`PanelHeader` from `./primitives`).

- [ ] **Step 5: Create the pages and router shell**

`src/pages/Landing.jsx` — today's full page, verbatim composition, state via the hook:
```javascript
import { Header } from "../components/Header";
import { SideRail } from "../components/SideRail";
import { Hero } from "../components/Hero";
import { SearchBand } from "../components/SearchBand";
import { Dashboard } from "../components/Dashboard";
import { FooterStrip } from "../components/FooterStrip";
import { useAsk } from "../lib/useAsk";

export default function Landing() {
  const ask = useAsk();
  return (
    <main className="min-h-screen bg-black">{/* keep App.jsx's current wrapper classes */}
      <Header />
      <SideRail />
      <Hero />
      <SearchBand query={ask.query} setQuery={ask.setQuery}
                  askBoostRAG={() => ask.submit()} isLoading={ask.isLoading} />
      <Dashboard answer={ask.answer} sources={ask.sources}
                 origin={ask.origin} error={ask.error} />
      <FooterStrip />
    </main>
  );
}
```
(Copy the real wrapper div/classes from today's `App()` return — preserve pixel-identical output.)

`src/pages/Research.jsx` — same, minus `Hero`, plus seeded query support:
```javascript
import { useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { Header } from "../components/Header";
import { SideRail } from "../components/SideRail";
import { SearchBand } from "../components/SearchBand";
import { Dashboard } from "../components/Dashboard";
import { FooterStrip } from "../components/FooterStrip";
import { useAsk } from "../lib/useAsk";

export default function Research() {
  const [params] = useSearchParams();
  const seeded = params.get("q") || "";
  const ask = useAsk(seeded);
  const seededOnce = useRef(false);
  useEffect(() => {
    if (seeded && !seededOnce.current) { seededOnce.current = true; ask.setQuery(seeded); }
  }, [seeded]);   // prefill only — never auto-submit (no surprise token spend)
  return (
    <main className="min-h-screen bg-black">
      <Header />
      <SideRail />
      <SearchBand query={ask.query} setQuery={ask.setQuery}
                  askBoostRAG={() => ask.submit()} isLoading={ask.isLoading} />
      <Dashboard answer={ask.answer} sources={ask.sources}
                 origin={ask.origin} error={ask.error} />
      <FooterStrip />
    </main>
  );
}
```

`src/App.jsx` becomes:
```javascript
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Landing from "./pages/Landing";
import Research from "./pages/Research";
import CategoryPage from "./pages/CategoryPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/research" element={<Research />} />
        <Route path="/category/:slug" element={<CategoryPage />} />
      </Routes>
    </BrowserRouter>
  );
}
```
(`CategoryPage` is built in Task 3 — create a minimal `pages/CategoryPage.jsx` returning `null` in this task so the build passes, replaced next task.)

- [ ] **Step 6: Gate**

Run: `npm run lint` (no NEW errors) and `npm run build` (succeeds).
Then `npm run dev` + open `http://localhost:5173` — the landing must look and behave EXACTLY as production does today (search included, backend running via `start-dev.ps1` pattern).

- [ ] **Step 7: Commit**

```bash
git add boostrag-frontend
git commit -m "refactor: decompose App.jsx into pages/components and add routing"
```

---

## Task 3: Beat 1 — CategoryPage + live nav

**Files:**
- Create: `src/pages/CategoryPage.jsx` (replacing the stub)
- Modify: `components/Header.jsx` and/or `components/Dashboard.jsx` (`CategoryPanel`) — nav buttons become router `Link`s; `components/Hero.jsx` — "Start Research" links to `/research`; `components/SearchBand.jsx` — example chips navigate to `/research?q=<chip text>`.

**Interfaces:**
- Consumes: `browseCategory(slug)` from Task 2's `api.js`; Task 1's `/browse` endpoint.
- Produces: `/category/:slug` pages in the current dark look; slugs exactly: `overview, engine, intake-exhaust, cooling, suspension, wheels-tires, braking, electronics`. Display names map: `{overview: "Overview", engine: "Engine", "intake-exhaust": "Intake & Exhaust", cooling: "Cooling", suspension: "Suspension", "wheels-tires": "Wheels & Tires", braking: "Braking", electronics: "Electronics"}` — export as `CATEGORY_LABELS` from `CategoryPage.jsx` for nav reuse.

- [ ] **Step 1: Implement `CategoryPage.jsx`**

```javascript
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Header } from "../components/Header";
import { FooterStrip } from "../components/FooterStrip";
import { Panel, PanelHeader } from "../components/primitives";
import { browseCategory } from "../lib/api";

export const CATEGORY_LABELS = {
  overview: "Overview", engine: "Engine", "intake-exhaust": "Intake & Exhaust",
  cooling: "Cooling", suspension: "Suspension", "wheels-tires": "Wheels & Tires",
  braking: "Braking", electronics: "Electronics",
};

export default function CategoryPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const label = CATEGORY_LABELS[slug];
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [ask, setAsk] = useState("");

  useEffect(() => {
    setData(null); setError("");
    if (!label) return;
    browseCategory(slug).then(setData).catch((e) => setError(e.message));
  }, [slug, label]);

  if (!label) {
    return (
      <main className="min-h-screen bg-black p-10 text-zinc-200">
        <p>Unknown category.</p><Link className="text-yellow-400" to="/">Back home</Link>
      </main>
    );
  }

  const items = data?.items ?? [];
  const scopedPlaceholder = `Ask about ${label.toLowerCase()} for the M340i...`;

  return (
    <main className="min-h-screen bg-black">
      <Header />
      <section className="mx-auto max-w-[1200px] px-5 py-10 lg:px-10">
        <h1 className="text-4xl font-black uppercase text-white">{label}</h1>

        <Panel className="mt-8 p-4">
          <PanelHeader title="In the library" />
          {error && <p className="text-red-400">{error}</p>}
          {!data && !error && <p className="text-zinc-500">Loading…</p>}
          {data && items.length === 0 && (
            <p className="text-zinc-400">
              This section of the library is growing. Ask BoostRAG anything about{" "}
              {label.toLowerCase()} below — it researches the live web and the best
              sources it finds join the library automatically.
            </p>
          )}
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {items.map((item, i) => (
              <article key={i} className="border border-zinc-800 bg-zinc-950/90 p-4">
                <h3 className="text-[15px] font-black text-white">{item.product || "Unknown source"}</h3>
                <p className="mt-1 text-[12px] font-semibold text-zinc-500">
                  {item.brand || "—"}{item.price ? ` • ${item.price}` : ""}
                </p>
                {item.text_preview && (
                  <p className="mt-2 line-clamp-3 text-[12px] text-zinc-400">{item.text_preview}</p>
                )}
                {item.url && (
                  <a href={item.url} target="_blank" rel="noreferrer"
                     className="mt-2 inline-block text-[12px] font-black uppercase text-yellow-400">
                    View Source
                  </a>
                )}
              </article>
            ))}
          </div>
        </Panel>

        <form className="mt-8 flex gap-2"
              onSubmit={(e) => { e.preventDefault();
                if (ask.trim()) navigate(`/research?q=${encodeURIComponent(ask.trim())}`); }}>
          <input value={ask} onChange={(e) => setAsk(e.target.value)}
                 placeholder={scopedPlaceholder}
                 className="flex-1 border border-zinc-700 bg-black px-4 py-3 text-zinc-100" />
          <button type="submit"
                  className="bg-yellow-400 px-6 py-3 font-black uppercase text-black">
            Ask
          </button>
        </form>
      </section>
      <FooterStrip />
    </main>
  );
}
```

- [ ] **Step 2: Wire the nav**

In the component that renders the eight tab buttons (`CategoryPanel` in `Dashboard.jsx`, plus any header/side nav duplicates): replace `<button>Overview</button>` etc. with `<Link to="/category/overview">…</Link>` using `CATEGORY_LABELS` for labels/slugs, preserving current styling classes. "Start Research" (Header/Hero) → `<Link to="/research">`. Example chips in `SearchBand.jsx`: `onClick` navigates to `/research?q=<encoded chip text>` when SearchBand is on the landing; when already on `/research` keep today's setQuery behavior (pass an optional `onChipSelect` prop; Research passes `setQuery`, Landing omits it → navigate).

- [ ] **Step 3: Gate**

`npm run lint` + `npm run build`; `npm run dev` — click every tab, confirm each category page loads with real corpus items (Intake & Exhaust shows ~7, Wheels & Tires shows the growing-state), CTA seeds `/research`.

- [ ] **Step 4: Commit**

```bash
git add boostrag-frontend
git commit -m "feat: category pages with live corpus browse and routed nav"
```

---

## Task 4: MERGE GATE — Beat 1 verification & deploy (controller + user)

- [ ] Backend suite green: `./.venv/Scripts/python.exe -m pytest tests/ --ignore=tests/test_ecs_scraper.py -q`.
- [ ] Browser pass on local dev: `/` pixel-identical to prod today (search works, both badges reachable); all 8 `/category/*` pages; deep-link reload on `/category/engine` (dev server); `/research?q=...` seeding; mobile viewport (375px).
- [ ] Merge to `main`, push. Confirm Render deploys (backend `/browse` live: `curl https://boostrag.onrender.com/browse?category=engine`) and Vercel deploys; **verify deep-link reload works on production** (`https://boost-rag.vercel.app/category/engine` — proves `vercel.json` rewrite).
- [ ] Full production browser pass (the Task-8 checklist, minus redesign items).

---

## Task 5: Beat 2 — tokens + motion vocabulary

**Files:**
- Create: `src/theme/tokens.js`
- Create: `src/components/motion.jsx` (shared motion primitives)
- Modify: `src/index.css` (Ken Burns keyframes + reduced-motion guard)

**Interfaces:**
- Produces: `tokens` object; `<Swell>` wrapper (hover scale 1.04, spring, ~150ms) and `<Reveal>` wrapper (fade/rise 12px on first in-view, 250ms) — both no-ops when `useReducedMotion()` is true; `.kenburns` CSS class.

- [ ] **Step 1: `src/theme/tokens.js`**

```javascript
// Two-zone design tokens — "showroom upstairs, garage downstairs".
export const tokens = {
  color: {
    // neutral scale
    white: "#FFFFFF", gallery: "#F6F6F4", fog: "#E8E8E6", steel: "#9CA3AF",
    graphite: "#27272A", tar: "#111113", black: "#0A0A0B",
    // M accents — jewelry, never flood (≤5% of any viewport)
    mBlue: "#0066B1", mRed: "#E7222E", streetYellow: "#FACC15",
  },
  font: {
    heading: "'Archivo', 'Inter', system-ui, sans-serif", // precise grotesk voice
    body: "'Inter', system-ui, sans-serif",
  },
  space: (n) => `${n * 8}px`, // 8px grid; showroom uses generous multipliers
  motion: {
    swellScale: 1.04, swellMs: 150, revealMs: 250, revealRise: 12, kenburnsS: 26,
  },
};
```

- [ ] **Step 2: `src/components/motion.jsx`**

```javascript
import { motion, useReducedMotion } from "framer-motion";
import { tokens } from "../theme/tokens";

export function Swell({ children, className = "" }) {
  const still = useReducedMotion();
  return (
    <motion.span className={`inline-block ${className}`}
      whileHover={still ? undefined : { scale: tokens.motion.swellScale }}
      transition={{ type: "spring", stiffness: 400, damping: 22 }}>
      {children}
    </motion.span>
  );
}

export function Reveal({ children, className = "" }) {
  const still = useReducedMotion();
  return (
    <motion.div className={className}
      initial={still ? false : { opacity: 0, y: tokens.motion.revealRise }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: tokens.motion.revealMs / 1000 }}>
      {children}
    </motion.div>
  );
}
```

- [ ] **Step 3: Ken Burns CSS in `src/index.css`**

```css
@keyframes kenburns {
  from { transform: scale(1.06) translate(0, 0); }
  to   { transform: scale(1.14) translate(-1.5%, -1%); }
}
.kenburns { animation: kenburns 26s ease-in-out infinite alternate; will-change: transform; }
@media (prefers-reduced-motion: reduce) {
  .kenburns { animation: none; }
}
```

- [ ] **Step 4: Apply `<Swell>`** to the nav tab links (Task 3's `Link`s), Header "Start Research", and Search/Ask buttons. Apply `<Reveal>` to landing value-prop cards and category-page sections. Gate: `npm run lint` + `npm run build` + dev-server check that hover swells and OS reduced-motion setting stills everything.

- [ ] **Step 5: Commit**

```bash
git add boostrag-frontend
git commit -m "feat: design tokens and motion vocabulary (swell, reveal, kenburns)"
```

---

## Task 6: Beat 2 — showroom Landing

**Files:**
- Modify: `src/pages/Landing.jsx` (full rewrite to showroom), `src/components/Hero.jsx` (or replace with new `ShowroomHero` inside Landing)
- Create: `src/assets/` hero image, `boostrag-frontend/ATTRIBUTIONS.md`

**Interfaces:**
- Consumes: `tokens`, `Swell`, `Reveal`, `CATEGORY_LABELS`, `OriginBadge`.
- Produces: light-zone landing per spec §7; garage pages untouched.

- [ ] **Step 1: Source the hero still.** Find on Unsplash/Pexels: a studio-lit performance car on a clean light background (search "car studio white", "sports car showroom"; prefer a dark BMW-adjacent silhouette but ANY marque works — no logo prominence). Download highest resolution to `src/assets/hero-studio.jpg` (target ≤ 400KB after compression — use squoosh-style quality ~75). Create `ATTRIBUTIONS.md`:
```markdown
# Image Attributions
- src/assets/hero-studio.jpg — Photographer Name, Unsplash (URL). Unsplash License (free commercial use).
```

- [ ] **Step 2: Rewrite `Landing.jsx`** (showroom zone — structure; classes may be tuned to taste at implementation):

```javascript
import { Link } from "react-router-dom";
import { Header } from "../components/Header";
import { FooterStrip } from "../components/FooterStrip";
import { OriginBadge } from "../components/AnswerPanel";
import { Swell, Reveal } from "../components/motion";
import { CATEGORY_LABELS } from "./CategoryPage";
import hero from "../assets/hero-studio.jpg";

// Real answer captured from production 2026-07-13 — static proof, zero token cost.
const PROOF = {
  origin: "corpus",
  question: "What downpipe options are there for the M340i?",
  answer: "For the BMW M340i, the main choices are VRSF's Track Limited Racing Downpipe (race) and the High Flow Catted Downpipe — catted keeps the CEL away; race maximizes flow.",
  source: { product: "VRSF B58 Downpipe", trust_tier: "Tier 1", price: "From $299.99" },
};

export default function Landing() {
  return (
    <main className="min-h-screen bg-[#F6F6F4] text-zinc-900">
      <Header light />  {/* Header gains a `light` variant prop: same layout, showroom palette */}

      {/* Hero — white studio, Ken Burns */}
      <section className="relative overflow-hidden">
        <img src={hero} alt="Performance car in a white studio" 
             className="kenburns h-[70vh] w-full object-cover" />
        <div className="absolute inset-0 flex flex-col items-start justify-center px-8 lg:px-24">
          <p className="text-sm font-bold uppercase tracking-[0.3em] text-zinc-600">
            Research smart. Build fast. Drive hard.
          </p>
          <h1 className="mt-4 max-w-3xl text-6xl font-black uppercase leading-none">
            The M340i Performance Advantage
          </h1>
          <Swell className="mt-8">
            <Link to="/research"
                  className="inline-block bg-zinc-900 px-8 py-4 font-black uppercase text-white">
              Start Research
              <span className="ml-3 inline-block h-3 w-1 bg-[#0066B1]" />
              <span className="inline-block h-3 w-1 bg-[#E7222E]" />
            </Link>
          </Swell>
        </div>
      </section>

      {/* Value props */}
      <section className="mx-auto grid max-w-6xl gap-10 px-8 py-24 md:grid-cols-3">
        {[["Precise Answers", "Backed by trusted sources & data"],
          ["Real-World Insights", "Community tested. Proven results."],
          ["Build Confidently", "The right parts. The right way."]].map(([t, s]) => (
          <Reveal key={t}>
            <h2 className="text-xl font-black uppercase">{t}</h2>
            <p className="mt-2 text-zinc-600">{s}</p>
          </Reveal>
        ))}
      </section>

      {/* Live proof strip */}
      <Reveal className="mx-auto max-w-3xl px-8 pb-24">
        <div className="border border-zinc-300 bg-white p-6 shadow-sm">
          <p className="text-sm font-semibold text-zinc-500">“{PROOF.question}”</p>
          <div className="mt-3"><OriginBadge origin={PROOF.origin} /></div>
          <p className="mt-2 text-[15px] leading-7">{PROOF.answer}</p>
          <p className="mt-3 text-xs font-bold uppercase text-zinc-500">
            {PROOF.source.product} · {PROOF.source.trust_tier} · {PROOF.source.price}
          </p>
        </div>
      </Reveal>

      {/* Category doorways — into the garage */}
      <section className="bg-zinc-900 px-8 py-24">
        <h2 className="mx-auto max-w-6xl text-3xl font-black uppercase text-white">
          Enter the garage
        </h2>
        <div className="mx-auto mt-10 grid max-w-6xl grid-cols-2 gap-4 md:grid-cols-4">
          {Object.entries(CATEGORY_LABELS).map(([slug, label]) => (
            <Swell key={slug}>
              <Link to={`/category/${slug}`}
                    className="block border border-zinc-700 bg-black p-6 font-black uppercase text-zinc-100 hover:border-yellow-400">
                {label}
              </Link>
            </Swell>
          ))}
        </div>
      </section>

      <FooterStrip />
    </main>
  );
}
```
Note: `OriginBadge` styling must read on a white card — if its classes assume dark background, add a `variant` prop rather than forking it. `Header light` variant: same structure, `text-zinc-900` on `bg-[#F6F6F4]`, keep nav links.

- [ ] **Step 3: Gate.** `npm run lint` + `npm run build`; dev pass: light landing, Ken Burns drifting, doorways route, `/research` still fully dark and functional (state now lives there; landing no longer needs `useAsk`).

- [ ] **Step 4: Commit**

```bash
git add boostrag-frontend
git commit -m "feat: showroom landing with kenburns hero, proof strip, category doorways"
```

---

## Task 7: Beat 2 — category heroes (real copy) + trust-chip labels

**Files:**
- Modify: `src/pages/CategoryPage.jsx` (hero intros), `src/components/AnswerPanel.jsx` + category card chip rendering (label map)

**Interfaces:**
- Produces: `CATEGORY_INTROS` map; `friendlyTier(raw)` label function used everywhere a trust chip renders.

- [ ] **Step 1: Add the eight intros** to `CategoryPage.jsx` (approved copy — edit freely on review):

```javascript
export const CATEGORY_INTROS = {
  overview:
    "Every build starts with a map. This is BoostRAG's library at a glance — every vetted source we hold on the M340i, across every system, growing with every question the community asks.",
  engine:
    "The B58 is the reason you bought the car. Tunes, turbo inlets, and the supporting mods that wake it up — with sources that separate proven power from forum folklore.",
  "intake-exhaust":
    "Airflow in, exhaust out — the first mods most builds touch and the ones with the most noise (in every sense). Catted vs. catless, intake gains, charge pipes: here's what the evidence actually says.",
  cooling:
    "Heat is the tax every tune pays. Intercoolers and heat exchangers keep the B58's power consistent on the third pull, not just the first — especially in summer traffic.",
  suspension:
    "Power is only half the build. Springs, coilovers, and the geometry that turns straight-line speed into a car that feels planted everywhere.",
  "wheels-tires":
    "Grip is the cheapest horsepower you'll ever buy. Fitment, widths, and the rubber that decides whether your build hooks or spins.",
  braking:
    "The fastest builds are the ones that can stop. Pads, rotors, and fluid that hold up after the fun starts — because fade is not a personality trait.",
  electronics:
    "The quiet layer that ties a modern build together — gauges, logging, and the data side of making a G20 do what you tell it.",
};
```
Render under the `<h1>`: `<p className="mt-4 max-w-2xl text-zinc-400 leading-7">{CATEGORY_INTROS[slug]}</p>` wrapped in `<Reveal>`.

- [ ] **Step 2: Unify trust-chip vocabulary.** Add to `AnswerPanel.jsx` and export:

```javascript
export function friendlyTier(raw) {
  const map = {
    "Tier 1": "Trusted vendor", "Tier 2": "Community", "Tier 3": "Unverified",
    strong_candidate: "Strong source", usable_candidate: "Usable source",
    weak_candidate: "Weak source", reject_or_manual_review: "Low confidence",
  };
  return map[raw] ?? raw;
}
```
Use `friendlyTier(source.trust_tier)` wherever chips render (research source cards + category cards). Raw value stays in the DOM as a `title` attribute for the curious.

- [ ] **Step 3: Gate + commit**

`npm run lint` + `npm run build`; dev pass of all 8 pages reading the intros, chips showing friendly labels.
```bash
git add boostrag-frontend
git commit -m "feat: category hero copy and human trust-tier labels"
```

---

## Task 8: MERGE GATE — Beat 2 verification & deploy (controller + user)

- [ ] Full local browser pass: landing (light, Ken Burns, proof strip, doorways), all 8 category pages (intros + live items + growing-states), `/research` (both origin badges via a corpus and a web query, friendly chip labels), seeded queries, mobile 375px, **OS reduced-motion on → all motion stilled**.
- [ ] `npm run lint` + `npm run build`; backend suite green.
- [ ] Merge to `main`, push; confirm Vercel + Render deploys.
- [ ] Production pass on https://boost-rag.vercel.app: repeat the browser checklist live; screenshot the landing + one category page as the record.
- [ ] Update project memory (Phase 1 shipped) and the ledger.

---

## Self-Review Notes (coverage map)

- Spec §4 routes/decomposition → Tasks 2–3. §5 `/browse` → Task 1. §6 tokens/motion/reduced-motion → Task 5. §7 category anatomy → Tasks 3 + 7; landing anatomy → Task 6; sparse states → Task 3. §8 two-beat delivery + gates → Tasks 4 and 8. §1 legal/attribution → Task 6 Step 1 + Global Constraints. §9 chip vocabulary → Task 7.
- Type consistency: `CATEGORY_LABELS` (Task 3) consumed in Task 6; `Swell`/`Reveal` (Task 5) consumed in Tasks 6–7; `browseCategory` (Task 2) consumed in Task 3; slugs identical across Tasks 1/3/6.
- Deliberate scope cuts (YAGNI): no frontend test framework; no SSR; no paid video; `SideRail`/`Hero` may be dropped from Research/Landing composition in Beat 2 only where the spec's anatomy says so.
- **Deviation from spec §5 (documented):** the "small in-process cache" for `/browse` is omitted — with ~17 metadata files a per-request read is microseconds; add a cache only if the corpus grows enough to matter.
