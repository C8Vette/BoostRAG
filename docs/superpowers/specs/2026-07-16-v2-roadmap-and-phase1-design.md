# BoostRAG v2 — Roadmap & Phase 1 (Content + Brand) Design Spec

**Date:** 2026-07-16
**Status:** Approved (design), pending implementation plan
**Scope of this spec:** the full v2 roadmap at summary level, and the **Phase 1 design in detail**. Phases 2–4 get their own spec → plan → build cycles when reached.

---

## 1. Context & Overriding Constraints

- BoostRAG is live: **https://boost-rag.vercel.app** (Vercel, frontend) → **https://boostrag.onrender.com** (Render Starter, backend). The owner applied to Anthropic's **Claude Corps fellowship (deadline 2026-07-17)** with this link.
- **Reviewer-may-click rule (hard):** from 7/17 onward, assume a reviewer can open the live site at any time. Nothing merges to `main` unless it is *complete and verified*; the production site is never half-redesigned.
- **Budget:** near-zero continues (~$7.25/mo hosting). New phases use free tiers until revenue exists.
- **Legal (hard):** no BMW-owned promotional footage or assets; no BMW trademarks (logo/roundel) as our UI branding. Imagery/video from licensed-free sources (Unsplash/Pexels commercial-use) or original work. Cars *appearing* in licensed photos is fine.
- Local dev (`start-dev.ps1`) keeps working unchanged through every phase.

## 2. The v2 Roadmap (agreed order: A → B → C → D)

| Phase | Name | Summary | Depends on |
|---|---|---|---|
| **A (this spec)** | Content & brand | Real pages for the 8 category tabs, routing, "showroom/garage" redesign, CSS motion. Frontend + one read-only endpoint. | — |
| **B** | Accounts & memory | Managed auth (e.g. Supabase/Clerk free tier), first real DB (Postgres): profiles, history, **My Garage** (user's car + mods). Login adds memory; it does not gate answers. Requires privacy policy + ToS. | — |
| **C** | Payments & tiers | Stripe subscriptions + entitlements. **Paid gets more** (stronger model, more daily web searches, deeper retrieval, saved garage); free never degrades below today. Tier routing plugs into the orchestrator's retriever seam. | B |
| **D** | Multi-vehicle | Vehicle registry, per-vehicle corpus/config/calibration, UI selector (lives on My Garage). **Start with B58 siblings** (M240i, M440i, X3 M40i, Supra) before other brands. 84 hardcoded BMW/M340i refs across 14 backend files to generalize. | easier after B |

Rationale for order: A improves what a fellowship reviewer sees at zero backend risk; B is the foundation C requires; D is the deepest re-architecture and gets cheaper after B (garage = natural vehicle selection) and C (revenue funds multi-corpus API costs).

## 3. Phase 1 Goals / Non-Goals

**Goals:** real destination pages for the eight nav categories; a landing page with showroom-grade polish; the two-zone design system; micro-motion; page content that *shows the live corpus* (hybrid model); decompose the monolithic `App.jsx`; one new read-only `/browse` endpoint.

**Non-Goals (deferred):** auth/DB (B), payments (C), multi-vehicle (D), SSR/SEO (a possible future Next.js migration — explicitly not now), paid stock video (revisit after the $0 hero is seen live), blog/guides content system.

## 4. Architecture

**Approach chosen:** evolve the existing Vite + React SPA with `react-router-dom` (no framework migration).

**Routes:**
```
/                    Landing (showroom)
/research            Ask experience (today's search + answer + sources, relocated)
/category/:slug      Category pages: overview, engine, intake-exhaust, cooling,
                     suspension, wheels-tires, braking, electronics
```
Nav tabs become real links. "Start Research" and example chips route to `/research` (chips seed the query).

**Frontend decomposition** (behavior-preserving refactor of the ~700-line `App.jsx`):
```
src/
  pages/        Landing.jsx, Research.jsx, CategoryPage.jsx
  components/   Header.jsx, SearchBand.jsx, AnswerPanel.jsx, SourceCard.jsx,
                OriginBadge.jsx, TrendingPanel.jsx, FooterStrip.jsx, Panel.jsx, ...
  theme/        tokens.js (shared design tokens for both zones)
  lib/          api.js (fetch wrapper for /ask and /browse)
```

**Vercel:** add SPA-fallback rewrite (all paths → `index.html`) so deep links work.

## 5. New Backend Endpoint — `GET /browse`

- **Request:** `GET /browse?category=<slug>`.
- **Slug → corpus `Category:` mapping:** `overview` → all; `engine` → Turbo Inlet, Tune; `intake-exhaust` → Intake, Downpipe, Charge Pipe; `cooling` → Cooling; `suspension` → Suspension; `wheels-tires` → Wheels & Tires; `braking` → Brakes; `electronics` → Electronics. Unknown slug → 404.
- **Response:** `{ "category": slug, "count": n, "items": [ { product, brand, price, url, trust_tier, text_preview } ] }`.
- **Source:** metadata JSONs under `storage.DATA_DIR/metadata`, filtered to `route == "cleaned"` (RAG-visible tier only) — so `/browse` shows exactly what retrieval can use, and auto-ingested sources appear as the flywheel grows.
- **Cost & safety:** pure metadata read — **no OpenAI/Tavily tokens**; same per-IP rate limit as `/ask`; small in-process cache. Does not count against `DAILY_ASK_CAP` (browsing is free by design).
- TDD, offline tests like all backend work.

## 6. Design System — "Showroom upstairs, garage downstairs"

Two visual **zones**; location determines temperature. The light→dark transition when moving from landing into working areas is intentional and load-bearing for the brand (BMW refinement × street culture).

- **Showroom** (`/`): gallery-white space, large quiet typography, one hero subject with slow Ken Burns drift, M-tricolor accents (`#0066B1`, `#E7222E`, existing yellow) used sparingly (accent ≤ ~5% of any viewport).
- **Garage** (`/research`, `/category/*`, later My Garage): evolved current dark aesthetic — near-black surfaces, red/yellow street accents, denser information layout.
- **Tokens** in `theme/tokens.js`: neutral scale white→near-black; accent palette + usage rules; heading grotesk + system body type; 8px spacing grid (generous multipliers in showroom, tighter in garage).

**Motion vocabulary** (all respect `prefers-reduced-motion` — animations disabled for users who request stillness):
- Hover swell on tabs/buttons: `scale(1.04)`, ~150ms, spring-ish ease.
- Ken Burns hero: 20–30s slow pan/zoom on a high-res licensed still ($0 approach first; licensed stock video is a possible later upgrade, decided after seeing the $0 version live).
- Entrance reveals: sections fade/rise 12px on first scroll into view (250ms, once).
- Answer arrival: brief settle animation on the research answer panel.

**Imagery rules:** licensed-free commercial-use sources only; alt text on all imagery; no BMW promo assets or trademarks as UI (see §1 Legal).

## 7. Page Anatomy

**Category page template** (one template × 8):
1. **Curated hero** — category name + 2–3 sentence editorial intro (drafted during implementation, owner-approved) + one atmospheric image. Garage styling.
2. **"In the library"** — live corpus product cards from `/browse`: product, brand, price, trust-tier chip, View Source link. Grows automatically via the flywheel.
3. **Sparse/empty state** — current coverage: Intake & Exhaust 7, Engine 4, Braking 2, Cooling 1, Suspension 1, **Wheels & Tires 0, Electronics 0**. Empty/sparse categories render an honest "this section of the library is growing — ask BoostRAG and it researches live" panel instead of an empty shelf (turns the gap into a live-research demo).
4. **Ask-this-category CTA** — search input pre-scoped to the category; routes to `/research` with the query seeded.

**Landing page** (showroom):
1. Hero: white-studio car still + Ken Burns, headline ("Research smart. Build fast. Drive hard."), single CTA → `/research`.
2. Three value props (kept, restyled for light space).
3. **Live proof strip** — a real miniature example answer (origin badge + one source card): show, don't tell.
4. Category doorways — the 8 categories as a visual grid linking into the garage zone.
5. Footer strip (adapted).

## 8. Delivery Discipline & Verification

- Branches: `feat/v2-phase1-*`. **Merge gate:** complete + verified only (reviewer-may-click rule).
- Two-beat delivery: **(1)** behavior-preserving decomposition + routing with the current look — verified live, merged; **(2)** redesign applied zone-by-zone, each beat verified live and merged whole. Production is never half-styled.
- Per-merge verification: `npm run lint` + `npm run build`; real-browser pass on the deployed preview — all routes, both origin badges, mobile viewport, `prefers-reduced-motion` enabled.
- `/browse` ships first (TDD, offline tests) since pages depend on it; backend suite stays green (`--ignore=tests/test_ecs_scraper.py` until the separate playwright track resolves).

## 9. Open Items Carried Forward

- Hero motion upgrade decision (licensed clip vs. keep CSS) — after the $0 version is live.
- Trust-chip vocabulary unification ("Tier 1" vs `strong_candidate`) — natural to fold into the redesign beat.
- Phase 2/3/4 specs — authored when their phase begins.
