# ECS Tuning B58 Scraper — Design Spec

**Date:** 2026-06-29
**Status:** Approved

---

## Goal

Automatically discover and ingest BMW B58-fitment product pages from ECS Tuning (`ecstuning.com`) into the BoostRAG `data/cleaned/` corpus. Target vehicles: M340i (G20), M240i (G26), M440i (G22), X3 M40i (G01), Z4 M40i (G29), 540i (G30), and other B58-powered chassis.

---

## Architecture

### New file: `boostrag-api/ecs_scraper.py`

A standalone script that discovers ECS product URLs, deduplicates against already-ingested content, then feeds new URLs into the existing `ingest_url()` pipeline.

**Existing code changes (minimal):**
- `ingest_urls.py / build_cleaned_text()` — accepts an optional `fitment` kwarg and writes a `Fitment:` header line when provided.
- No changes to `preprocess.py`, `source_ranker.py`, `chunk_embed.py`, or `main.py`.

### Components

| Function | File | Responsibility |
|---|---|---|
| `get_product_urls(category_url)` | `ecs_scraper.py` | Paginates an ECS category page; returns all product URLs found |
| `get_ingested_urls()` | `ecs_scraper.py` | Scans `data/metadata/*.json`; returns set of previously-ingested URLs |
| `extract_ecs_price(soup)` | `ecs_scraper.py` | Pulls base price from `application/ld+json`; falls back to `extract_price()` from `ingest_urls.py` |
| `extract_fitment(soup)` | `ecs_scraper.py` | Parses ECS compatibility section; returns list of chassis codes e.g. `["G20", "G29", "G01"]` |
| `scrape_ecs_b58(...)` | `ecs_scraper.py` | Orchestrator: discover → dedup → rate-limited ingest loop |

---

## Data Flow

```
ecs_scraper.py
  │
  ├── 1. Read configured category URLs (hardcoded list of ECS B58 category pages)
  │
  ├── 2. For each category URL → paginate → collect product URLs
  │
  ├── 3. Dedup: filter URLs already present in data/metadata/*.json
  │        (--force bypasses dedup)
  │
  └── 4. For each new product URL (rate-limited, 1–2s delay):
           ├── fetch HTML
           ├── extract_ecs_price(soup)   → base price (JSON-LD first, regex fallback)
           ├── extract_fitment(soup)     → ["G20", "G29", "G01"]
           └── ingest_url(url)           → writes .txt + .json via existing pipeline
```

`ingest_url()` handles all trust scoring, routing, and file writing. The scraper's only additions are the ECS-specific price and fitment extraction, which are passed in before calling `ingest_url()`.

---

## Schema Addition

The corpus `.txt` header gains one optional field:

```
Brand: ECS Tuning
Category: Intake
Vehicle: BMW M340i G20
Fitment: G20, G29, G01, F30
Price: $349.00
Source Type: product_page
...
```

`preprocess.py`'s existing key:value parser picks up `Fitment` automatically. Files ingested without it simply won't have the key — fully backward compatible with the existing corpus.

---

## Price Extraction

ECS product pages embed `application/ld+json` structured data with clean `price` and `priceCurrency` fields. Strategy:

1. Parse `<script type="application/ld+json">` — extract `offers.price` (base product price only).
2. If absent or unparseable, fall back to `extract_price()` from `ingest_urls.py`.

Core deposits (e.g., `+ $150 core`) and option add-ons (e.g., `+ $200 catless`) appear as separate line items in the page text and are excluded by targeting only the primary `offers.price` field in JSON-LD.

---

## Discovery

**Strategy: Category page crawl.**

Start from a hardcoded list of ECS B58 category entry-point URLs (e.g., their BMW G20 performance catalog pages). For each:
1. Parse pagination links to find all pages in the category.
2. Extract product URLs from each page.
3. Collect into a deduplicated URL set before ingesting.

The hardcoded category list lives at the top of `ecs_scraper.py` as a constant, making it easy to add new categories without changing logic.

---

## Deduplication & Re-scraping

**Default:** Skip URLs already present in `data/metadata/*.json` (matched by the `url` field).

**`--force` flag:** Re-scrapes and overwrites all URLs, including previously ingested ones. Use this for price refresh runs.

Age-based staleness (auto-refresh after N days) is out of scope for this version.

---

## CLI

```bash
# Full run — only ingest new products
python ecs_scraper.py

# Force re-scrape all (price refresh)
python ecs_scraper.py --force

# Dry run — print what would be ingested, no writes
python ecs_scraper.py --dry-run --limit 20

# Single category only
python ecs_scraper.py --category intakes
```

`--dry-run` is the recommended first run mode: inspect the discovered URLs and extracted metadata before committing to writes.

---

## Rate Limiting & Politeness

- 1–2 second sleep between every HTTP request (both category pages and product pages).
- Check `ecstuning.com/robots.txt` via `urllib.robotparser` once at startup; abort if target paths are disallowed.
- Reuse the existing `BoostRAG/0.2 source ingestion bot` User-Agent string from `ingest_urls.py`.

---

## Testing

### Fixtures

```
boostrag-api/tests/
  fixtures/
    ecs_category_page.html      # Category page with pagination + product links
    ecs_product_intake.html     # Product with JSON-LD price + multi-chassis fitment
    ecs_product_downpipe.html   # Product with core deposit price (tests fallback)
  test_ecs_scraper.py
```

Fixtures are saved snapshots of real ECS HTML pages, added to the repo. New fixtures are added when ECS changes their page structure.

### Test Coverage

| Test | What it validates |
|---|---|
| `test_get_product_urls` | Correct URLs extracted from category fixture; pagination followed |
| `test_extract_ecs_price_json_ld` | Base price pulled from JSON-LD structured data |
| `test_extract_ecs_price_fallback` | Regex fallback fires when JSON-LD absent; core deposit excluded |
| `test_extract_fitment` | Correct chassis list returned from fitment section |
| `test_get_ingested_urls` | Reads existing metadata JSONs; returns correct URL set |
| `test_dedup_skips_known` | `scrape_ecs_b58()` skips URLs in ingested set (ingest_url mocked) |
| `test_force_flag_overrides_dedup` | `--force` causes known URLs to be re-scraped |

`ingest_url()` is mocked in all tests — no real HTTP calls, no OpenAI usage.

---

## Out of Scope

- Age-based automatic re-scraping (future)
- Ingesting ECS editorial/blog content (not product pages)
- Other vendors (BMS, Turner, etc.) — separate scrapers if needed
- JS-rendered pages (ECS product pages are server-rendered; this is not needed)
- Automatic ChromaDB rebuild after scraping (run `chunk_embed.py` manually afterward)
