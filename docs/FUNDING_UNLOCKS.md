# What Funding Unlocks — BoostRAG

> A living doc: what money buys, in what order, and roughly what it costs.
> Organized **Now → Next → Later** so spend follows leverage. Costs are ballpark
> monthly (USD) unless noted. Update as things firm up.

**Context:** BoostRAG is a BMW M340i aftermarket-parts research assistant — a local
RAG pipeline (ChromaDB + OpenAI embeddings) behind a FastAPI backend and a
React/Vite frontend, with a live web-research layer (Tavily). Built to date on a
near-zero budget. Live demo: frontend on Vercel, backend on Render, accounts on
Supabase.

---

## The one-line thesis for spend

> Money first goes to **making the demo undeniable** (cheap, high-visibility),
> then to the **product moat** (corpus depth + answer quality), then to **scale
> and monetization**. The single highest-leverage line item at every stage is
> *the founder's time*.

---

## NOW — small money, immediate leverage (~$40–80/mo total)

These make the thing you show an investor visibly better, and most are constraints
we are actively hitting.

| Item | Why it matters | Rough cost |
|---|---|---|
| **Supabase Pro** | Free tier auto-pauses after ~1 week idle → accounts DB "falls asleep" mid-demo. Pro removes the pause and raises limits. Cheapest "looks professional" win. | ~$25/mo |
| **Stronger generation model + higher API caps** | Directly fixes the answer-quality gap (e.g. "higher exhaust note" returning only a downpipe instead of exhausts, cutouts, dump valves). Today we rate-limit and cap hard because every query costs money. Budget → deeper, multi-part answers. Also the foundation of the paid-tier thesis (free = good answer, paid = deep answer). | Usage-based; a demo-safe cap is single/low-double digits/mo |
| **Persistent vector storage** | Corpus is currently rebuilt from scratch on each deploy (Render's cheap tier has no disk). A small paid tier / attached disk fixes cold starts and reliability. | ~$7–20/mo |
| **Custom domain** | `boostrag.com` instead of `*.vercel.app`. Small cost, real credibility signal. | ~$12/yr |
| **Licensed hero imagery** | A real, licensed aggressive M-car hero (the GT3-style front-end look) on the landing/sign-in pages instead of placeholders. Must be commercial-use licensed — never BMW rights-managed/press assets. | one-time, low $ |

---

## NEXT — real product investment (hundreds/mo)

Where BoostRAG stops looking like a demo and starts being a tool people trust.

| Item | Why it matters | Rough cost |
|---|---|---|
| **Corpus depth & breadth** | The product *is* the data. More ingestion, broader coverage (beyond just the M340i / B58), possibly licensed content. This is the moat. | ingestion time + data/licensing |
| **Retrieval quality** | Reranking models, larger embeddings, better answer synthesis — the gap between "a chatbot" and "the source builders trust." | usage-based |
| **Live-research layer wired in** | Tavily web search exists but isn't in the main answer path yet; funding makes generous live research viable per query. | usage-based |
| **Founder time** | Money that buys focus (part- or full-time) beats any single infra upgrade. Highest-leverage line item, full stop. | — |

---

## LATER — scale & monetization

Once there's traction to justify it.

| Item | Why it matters | Rough cost |
|---|---|---|
| **Paid-tier infrastructure** | Real billing (Stripe), usage metering, tiered answer-depth productized. Turns the free/paid thesis into revenue. | platform fees + build time |
| **Managed vector DB at scale** | Move off local Chroma to Pinecone/Qdrant/Weaviate when corpus + traffic outgrow a single box. | scales with usage |
| **Multi-vehicle expansion** | Generalize the pipeline beyond the M340i to other platforms — each new platform is a new market. | ingestion + compute |
| **A second pair of hands** | Contractor or hire once the roadmap outpaces one person. | market rate |

---

## Explicitly NOT in this doc

**Deal terms** — equity, valuation, SAFE vs. convertible note, raise amount. Those
are a lawyer-and-accountant conversation, not an engineering one. Get real
professional advice before signing anything. This doc only covers *what the money
buys and why*.

---

## Open product threads this funding would accelerate

- **Answer-quality redesign** — tighter formatting, more expansive/complete answers,
  and tier-gated depth (the "exhaust note" problem). Currently parked for its own
  brainstorm.
- **Accounts & My Garage (v2 Phase 2)** — in progress; personalizes answers to the
  user's exact build. Paid tiers make richer personalization worthwhile.
- **Brand & design system** — "showroom upstairs, garage downstairs"; a licensed
  hero and custom domain complete the first impression.
