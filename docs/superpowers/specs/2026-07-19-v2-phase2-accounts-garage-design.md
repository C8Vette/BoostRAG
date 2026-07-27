# v2 Phase 2 — Accounts & My Garage Design Spec

**Date:** 2026-07-19
**Status:** Approved (design), pending implementation plan
**Scope:** User accounts (Supabase auth) + "My Garage" (per-user car + mods) that personalizes answers. First stateful backend for BoostRAG.

---

## 1. Context & Overriding Constraints

- BoostRAG is live: **https://boost-rag.vercel.app** (Vercel, frontend) → **https://boostrag.onrender.com** (Render, backend). Applied to Anthropic's Claude Corps fellowship — **reviewer-may-click rule holds:** nothing merges to `main` unless complete + verified; the production site is never half-built.
- **Budget:** near-zero. Supabase free tier (Postgres + auth). No new fixed cost.
- **Login is additive, never a gate (v1):** signing in adds memory (a garage); it does NOT gate answers. Anonymous users keep full access. (Credit-gating is a deliberate *future* switch — see §2 entitlements — turned on only when a logged-in user's granted credits run out; not built in v1.)
- **Degrade gracefully (hard rule):** if Supabase (auth or DB) is unavailable/paused/slow, `/ask` still answers as an anonymous visitor. A database outage must never break the demo. This neutralizes Supabase free-tier's ~1-week idle pause for the fellowship scenario.
- Local dev (`start-dev.ps1`) keeps working; auth/garage features no-op cleanly when Supabase env vars are absent locally.
- Additive only: logged-out behavior is byte-identical to today.

## 2. Roadmap Position

Phase A (content/brand) shipped. **This is Phase B.** It is the foundation Phase C (payments/tiers) builds on — hence the entitlements columns seeded now. **Deferred to later phases:** answer history, "was this helpful?" feedback loop, **saved parts/wishlist** (owner likes this — explicit Phase 3 candidate), and multi-vehicle/fleet (Phase 4).

## 3. Architecture & Auth Flow

Frontend uses `supabase-js` for login; Supabase Auth issues a signed JWT; the browser sends `Authorization: Bearer <jwt>` on requests; FastAPI verifies the JWT signature and extracts the user id — the backend never handles passwords.

```
Browser (Vercel)              Supabase                    Render (FastAPI)
 supabase-js login  ──sign in──► Auth (issues JWT) ──►
 session (JWT) ◄────────────────
 POST /ask + Bearer JWT ───────────────────────────────► optional_user: verify JWT,
 garage CRUD + Bearer JWT ──────────────────────────────► load garage, inject context,
                              Postgres (+ RLS) ◄──────────  answer (RLS-scoped reads)
```

**Three critical guardrails (called out because they are the classic traps):**
1. **Two keys, never mixed:** the **anon key** is public → frontend (`VITE_SUPABASE_ANON_KEY`). The **service-role key** bypasses all security → Render env only (`SUPABASE_SERVICE_ROLE_KEY`), never in frontend, never committed.
2. **Row Level Security (RLS) is non-optional — AND the backend must still filter explicitly.** Postgres RLS policies (`user_id = auth.uid()`) are enabled on every table in the first migration. **Critical:** all garage DB access in this design goes through the FastAPI backend using the **service-role key, which BYPASSES RLS.** So RLS here is defense-in-depth (protecting against any accidental direct anon-key access), NOT the primary control — every backend query MUST explicitly filter by the authenticated user's id (`.eq("user_id", uid)`), and inserts MUST stamp it. Never trust a `user_id`/`garage_id` from the request body; derive it from the verified JWT. This is the single most important correctness rule in the phase.
3. **Degrade gracefully:** every auth/garage call in the `/ask` path is wrapped so Supabase errors/timeouts are swallowed and the request proceeds context-free.

## 4. Data Model (Supabase Postgres)

**`profiles`** — one row per user; extends built-in `auth.users`; auto-created by a signup trigger.
```
id            uuid  PK, references auth.users(id)
display_name  text  null
plan          text  default 'free'      -- Phase 3 entitlements hook (unused in v1)
credits       int   default 0           -- reserved for future gating (unused in v1)
created_at    timestamptz default now()
```

**`garages`** — one per user, one car per garage.
```
id            uuid PK default gen_random_uuid()
user_id       uuid references profiles(id) UNIQUE   -- one garage per user
year          int
model         text                                  -- e.g. "M340i"
trim          text null                              -- e.g. "xDrive"
context_on    bool default true                      -- persisted personalization toggle
created_at    timestamptz default now()
updated_at    timestamptz default now()
```

**`garage_mods`** — accumulating build sheet, one row per mod.
```
id            uuid PK default gen_random_uuid()
garage_id     uuid references garages(id) on delete cascade
category      text                                   -- matches corpus categories
name          text                                   -- free text OR chosen corpus product
source_url    text null                              -- set if added from a real corpus part
created_at    timestamptz default now()
```

**RLS:** all three tables — `profiles` policy `id = auth.uid()`; `garages` policy `user_id = auth.uid()`; `garage_mods` policy via join `garage_id in (select id from garages where user_id = auth.uid())`. Written in the first migration.

**One car per user in v1** — fleet/multi-vehicle is Phase 4 (drop the `UNIQUE`, add a selector then). Not modeled now (YAGNI).

**Context block** built from these tables when `context_on` (example):
> "The user drives a 2021 BMW M340i xDrive. Installed modifications: VRSF catted downpipe (Intake & Exhaust), BM3 tune (Engine), CSF intercooler (Cooling). Tailor advice to this setup; note when a recommendation assumes a different configuration."

The final clause makes the model *flag* divergence from the user's build rather than silently assume it.

## 5. Backend API (all additive)

**`auth.py` (new)** — FastAPI dependency verifying the Supabase JWT (signature against Supabase's JWT secret, `SUPABASE_JWT_SECRET` in Render env):
- `require_user` → returns user id, raises 401 if missing/invalid (for `/garage`).
- `optional_user` → returns user id or `None`, never raises (for `/ask`, preserving anonymous access).

**Garage endpoints** (require a valid user; DB access via the backend service-role client which bypasses RLS, so EVERY query filters `.eq("user_id", uid)` and every insert stamps the JWT-derived uid — never a body-supplied id; see §3 guardrail 2):
```
GET    /garage            → { garage, mods } or 204 if none
PUT    /garage            → create/update car (year, model, trim, context_on)
POST   /garage/mods       → add mod { category, name, source_url? }
DELETE /garage/mods/{id}  → remove a mod
```

**`/ask` change** (the personalization payoff):
- Accepts `optional_user` + a request flag `use_context: bool = true`.
- If logged in AND `garage.context_on` AND `use_context`: load garage (wrapped/degrading), build the context block, pass to the orchestrator as `user_context: str | None`; `answer.generate_answer` prepends it to the grounded prompt when present.
- Retrieval path (corpus, web fallback, confidence, badges) UNCHANGED. Anonymous or toggle-off requests hit today's exact code path.

**Answer cache fix (the one easy-to-miss bug):** the cache key must include a **context fingerprint** (a hash of the injected context block, empty when none) so two users asking the same question with different garages don't collide. Without this, one user's personalized answer could be served to another.

**Cost:** garage context adds input tokens per call (negligible); does NOT change the web-search fuse or `DAILY_ASK_CAP`.

**Testing (offline, mocked — no live Supabase):** `auth.py` with forged/expired/valid tokens; garage endpoints with a mocked DB layer; `/ask` asserting the context block reaches `generate_answer` and that the cache key differs by context; graceful-degradation asserted by simulating a garage-load failure and confirming a normal answer.

## 6. Frontend

- **Auth UI:** Supabase prebuilt sign-in (email + Google) at `/login` + header "Sign in"; logged-in shows name + menu. Styled to the design system.
- **`lib/supabase.js`:** client using `VITE_SUPABASE_ANON_KEY` + `VITE_SUPABASE_URL`; an auth-context provider exposes the current user; `lib/api.js` attaches the JWT to requests when present.
- **`/garage` page (garage zone aesthetic):** car selector (year/model/trim), mods list with **corpus-autocomplete** "add mod" input (autocomplete sourced from `/browse` data), delete buttons, and the **"Use my garage in answers"** toggle (persists `context_on`).
- **Progressive capture:** on answer source cards and category part cards, an *"Own this? Add to garage"* action (shown only when logged in) that one-taps a mod in — the garage fills through normal use.
- **Context indicator on `/research`:** a visible "Personalized for your M340i · on/off" control (per-request `use_context`), so users always know if their build is shaping the answer and can flip it.

## 7. Delivery Discipline (two gated beats)

- Branches `feat/v2-phase2-*`. **Merge gate:** complete + verified only.
- **Beat 1 — backend/auth foundation:** Supabase project + migrations + RLS, `auth.py`, garage endpoints, `/ask` context wiring + cache-key fix. Behind tests. NO visible UI change → merges safely (logged-out identical).
- **Beat 2 — frontend:** login UI, garage page, progressive-add, toggle. Verified live: width matrix 375–2560 (incl. 1200px), logged-out AND logged-in, AND the graceful-degradation path (simulate DB down → `/ask` still answers).
- Each beat ends at a controller+user merge gate.

## 8. User-Owned Setup Steps (controller cannot do — no account creation / secret handling)

- Create the Supabase project; run the provided SQL migrations (controller supplies exact SQL).
- Set env vars: Render — `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`; Vercel — `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.
- Enable Google OAuth in Supabase if desired (email/password works without it).

## 9. Non-Goals / Future

- Answer history, "was this helpful?" feedback → later phase.
- **Saved parts/wishlist → Phase 3 candidate (owner-favored).**
- Multi-vehicle/fleet → Phase 4 (schema extends cleanly).
- Credit-gating enforcement → Phase 3 (columns seeded now).
- Rolling our own auth → explicitly rejected (security risk).
