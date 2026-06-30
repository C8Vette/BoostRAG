# ECS Tuning B58 Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `ecs_scraper.py` that crawls ECS Tuning B58 category pages, deduplicates against existing ingested content, and ingests new product pages into `data/cleaned/` via the existing `ingest_url()` pipeline.

**Architecture:** Standalone `boostrag-api/ecs_scraper.py` with five focused functions plus internal URL discovery helpers. The only changes to existing code are optional `fitment` and `price_override` kwargs on `ingest_url()` and `build_cleaned_text()` in `ingest_urls.py`. Tests use saved HTML fixture files — no real HTTP, no OpenAI calls.

**Tech Stack:** Python 3.11+, requests, BeautifulSoup4/lxml, pytest, json, re, time, urllib.robotparser

## Global Constraints

- Rate limit: 1.5 second sleep between every HTTP request
- User-Agent: `BoostRAG/0.2 source ingestion bot (automotive research assistant; local development)` (reuse from `ingest_urls.py`)
- `ecstuning.com/robots.txt` checked once at scraper startup; raise `RuntimeError` and abort if crawling is disallowed
- `ingest_url()` is NEVER called in tests — always mock it
- No real HTTP in tests — all parsing tests use fixture HTML files loaded from disk
- All tests run from `boostrag-api/`: `pytest tests/ -v`
- Install pytest if needed: `pip install pytest` (inside `.venv`)

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `boostrag-api/ingest_urls.py` | Add `fitment` and `price_override` kwargs to `build_cleaned_text()` and `ingest_url()` |
| Create | `boostrag-api/ecs_scraper.py` | All scraper logic: discovery, extraction, dedup, orchestrator, CLI |
| Create | `boostrag-api/tests/__init__.py` | Makes `tests/` a package for pytest discovery |
| Create | `boostrag-api/tests/fixtures/ecs_category_page.html` | Category page fixture with product links + pagination |
| Create | `boostrag-api/tests/fixtures/ecs_product_intake.html` | Product page with JSON-LD price + multi-chassis fitment |
| Create | `boostrag-api/tests/fixtures/ecs_product_downpipe.html` | Product page without JSON-LD (tests regex fallback + core deposit exclusion) |
| Create | `boostrag-api/tests/test_ingest_extensions.py` | Tests for the new `ingest_urls.py` kwargs |
| Create | `boostrag-api/tests/test_ecs_scraper.py` | All scraper unit tests |

---

### Task 1: Extend `ingest_url()` and `build_cleaned_text()` with fitment and price_override

**Files:**
- Modify: `boostrag-api/ingest_urls.py` — `build_cleaned_text()` at line 282, `ingest_url()` at line 323
- Create: `boostrag-api/tests/__init__.py`
- Create: `boostrag-api/tests/test_ingest_extensions.py`

**Interfaces:**
- Produces: `build_cleaned_text(..., fitment: list[str] | None = None)` — writes `Fitment: G20, G29` line after Vehicle when provided
- Produces: `ingest_url(url, *, fitment: list[str] | None = None, price_override: str | None = None)` — passes both through; uses `price_override` in place of regex price when supplied

- [ ] **Step 1: Create `tests/__init__.py`**

Create `boostrag-api/tests/__init__.py` as an empty file. This makes `tests/` a package so pytest discovers it correctly.

```python
```

- [ ] **Step 2: Write failing tests for the new kwargs**

Create `boostrag-api/tests/test_ingest_extensions.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ingest_urls import build_cleaned_text

MINIMAL_SCORE = {
    "source_type": "product_page",
    "trust_tier": 1,
    "review_status": "auto_approved",
    "claim_types": ["fitment"],
    "risk_flags": [],
    "reason": "Test",
}

BASE_KWARGS = dict(
    title="Test Product",
    url="https://www.ecstuning.com/b-ecs/ES123/",
    domain="ecstuning.com",
    description=None,
    brand="ECS Tuning",
    category="Intake",
    vehicle="BMW M340i G20",
    price="$349.00",
    body_text="Great intake for the B58.",
    score=MINIMAL_SCORE,
)


def test_build_cleaned_text_includes_fitment_when_provided():
    result = build_cleaned_text(**BASE_KWARGS, fitment=["G20", "G29", "G01"])
    assert "Fitment: G20, G29, G01" in result


def test_build_cleaned_text_fitment_appears_after_vehicle():
    result = build_cleaned_text(**BASE_KWARGS, fitment=["G20"])
    vehicle_pos = result.index("Vehicle:")
    fitment_pos = result.index("Fitment:")
    price_pos = result.index("Price:")
    assert vehicle_pos < fitment_pos < price_pos


def test_build_cleaned_text_omits_fitment_line_when_none():
    result = build_cleaned_text(**BASE_KWARGS)
    assert "Fitment:" not in result


def test_build_cleaned_text_price_in_output():
    result = build_cleaned_text(**BASE_KWARGS)
    assert "Price: $349.00" in result
```

- [ ] **Step 3: Run tests to confirm they fail**

```
cd boostrag-api
pytest tests/test_ingest_extensions.py -v
```

Expected: 2 FAIL with `TypeError: build_cleaned_text() got an unexpected keyword argument 'fitment'`. The price test should pass already.

- [ ] **Step 4: Modify `build_cleaned_text()` in `ingest_urls.py`**

Change the function signature (line 282) and body. Replace the entire function:

```python
def build_cleaned_text(
    *,
    title: str,
    url: str,
    domain: str,
    description: str | None,
    brand: str,
    category: str,
    vehicle: str,
    price: str,
    body_text: str,
    score: dict,
    fitment: list[str] | None = None,
) -> str:
    claim_types = ", ".join(score["claim_types"])
    risk_flags = ", ".join(score["risk_flags"]) if score["risk_flags"] else "None"
    fitment_line = f"\n    Fitment: {', '.join(fitment)}" if fitment else ""

    metadata_header = f"""
    Source Title: {title}
    Source URL: {url}
    Source Domain: {domain}
    Brand: {brand}
    Category: {category}
    Vehicle: {vehicle}{fitment_line}
    Price: {price}
    Source Type: {score["source_type"]}
    Trust Tier: {score["trust_tier"]}
    Review Status: {score["review_status"]}
    Claim Types: {claim_types}
    Risk Flags: {risk_flags}
    Source Ranking Reason: {score["reason"]}
    Date Ingested: {datetime.now(timezone.utc).isoformat()}
    """

    if description:
        metadata_header += f"\nMeta Description: {description}\n"

    metadata_header = textwrap.dedent(metadata_header).strip()

    return f"{metadata_header}\n\n--- Extracted Page Text ---\n\n{body_text}"
```

- [ ] **Step 5: Modify `ingest_url()` in `ingest_urls.py`**

Change the function signature at line 323:

```python
def ingest_url(
    url: str,
    *,
    fitment: list[str] | None = None,
    price_override: str | None = None,
) -> tuple[Path, Path, dict]:
```

Inside `ingest_url()`, replace the line `price = extract_price(body_text)` with:

```python
price = price_override if price_override is not None else extract_price(body_text)
```

Update the `build_cleaned_text()` call to pass `fitment`:

```python
cleaned_text = build_cleaned_text(
    title=title,
    url=url,
    domain=domain,
    description=description,
    brand=brand,
    category=category,
    vehicle=vehicle,
    price=price,
    body_text=body_text,
    score=score,
    fitment=fitment,
)
```

Update the `metadata` dict to include `fitment` when present:

```python
metadata = {
    "title": title,
    "url": url,
    "domain": domain,
    "description": description,
    "brand": brand,
    "category": category,
    "vehicle": vehicle,
    "price": price,
    **({"fitment": fitment} if fitment else {}),
    **score,
    "text_file": str(txt_path),
    "metadata_file": str(json_path),
    "date_ingested": datetime.now(timezone.utc).isoformat(),
}
```

- [ ] **Step 6: Run tests to confirm they pass**

```
pytest tests/test_ingest_extensions.py -v
```

Expected: 4 PASS

- [ ] **Step 7: Commit**

```bash
git add boostrag-api/ingest_urls.py boostrag-api/tests/__init__.py boostrag-api/tests/test_ingest_extensions.py
git commit -m "feat: extend ingest_url with fitment and price_override kwargs"
```

---

### Task 2: Create HTML fixtures and implement `get_ingested_urls()`

**Files:**
- Create: `boostrag-api/tests/fixtures/ecs_category_page.html`
- Create: `boostrag-api/tests/fixtures/ecs_product_intake.html`
- Create: `boostrag-api/tests/fixtures/ecs_product_downpipe.html`
- Create: `boostrag-api/ecs_scraper.py`
- Create: `boostrag-api/tests/test_ecs_scraper.py`

**Interfaces:**
- Produces: `get_ingested_urls() -> set[str]` — reads `data/metadata/*.json`, returns set of `"url"` values

> **Note on fixtures:** These HTML files model the expected ECS page structure based on their known JSON-LD and URL patterns. Before running the scraper against the live site, open a real ECS product page, inspect the HTML, and verify that: (1) `<script type="application/ld+json">` contains `offers.price`, (2) chassis codes appear in parentheses like `(G20)`, (3) product links contain `/ES\d+/`. Update the fixtures if ECS's actual structure differs.

- [ ] **Step 1: Create fixture directory and HTML files**

Create `boostrag-api/tests/fixtures/ecs_category_page.html`:

```html
<!DOCTYPE html>
<html>
<head><title>BMW G20 B58 Performance | ECS Tuning</title></head>
<body>
  <ul class="listing-items">
    <li>
      <a href="https://www.ecstuning.com/b-ecs-tuning/s-intake/ES4563456/">
        ECS B58 Intake System
      </a>
    </li>
    <li>
      <a href="https://www.ecstuning.com/b-vrsf/s-charge-pipe/ES7891234/">
        VRSF B58 Charge Pipe
      </a>
    </li>
    <li>
      <a href="/b-ecs-tuning/s-heat-exchanger/ES1122334/">
        ECS B58 Heat Exchanger
      </a>
    </li>
  </ul>
  <a rel="next" href="https://www.ecstuning.com/b-BMW/c-B58/?page=2">Next</a>
</body>
</html>
```

Create `boostrag-api/tests/fixtures/ecs_product_intake.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <title>ECS Tuning B58 Intake System | ECS Tuning</title>
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "ECS Tuning B58 Intake System",
    "offers": {
      "@type": "Offer",
      "price": "349.00",
      "priceCurrency": "USD"
    }
  }
  </script>
</head>
<body>
  <h1>ECS Tuning B58 Intake System</h1>
  <div class="es-fitment">
    <h3>Vehicle Fitment</h3>
    <ul>
      <li>2019-2023 BMW M340i (G20)</li>
      <li>2019-2023 BMW Z4 M40i (G29)</li>
      <li>2020-2023 BMW X3 M40i (G01)</li>
      <li>2016-2019 BMW 340i (F30)</li>
    </ul>
  </div>
  <div class="product-description">
    <p>High-flow intake system for B58 engines. Fits G20, G29, G01, F30 platforms.
       Drop-in replacement. Installs in under 30 minutes.</p>
  </div>
</body>
</html>
```

Create `boostrag-api/tests/fixtures/ecs_product_downpipe.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <title>ECS B58 Catted Downpipe | ECS Tuning</title>
</head>
<body>
  <h1>ECS B58 Catted Downpipe</h1>
  <div class="es-fitment">
    <h3>Vehicle Fitment</h3>
    <ul>
      <li>2019-2023 BMW M340i (G20)</li>
      <li>2022-2023 BMW M240i (G26)</li>
    </ul>
  </div>
  <div class="product-description">
    <p>Price: $549.00</p>
    <p>Core Deposit: + $150.00</p>
    <p>High-quality catted downpipe for the B58 engine. Gains 15-20hp with tune.</p>
  </div>
</body>
</html>
```

- [ ] **Step 2: Create `ecs_scraper.py` with imports and `get_ingested_urls()`**

Create `boostrag-api/ecs_scraper.py`:

```python
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.robotparser
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from ingest_urls import ingest_url, extract_price

METADATA_DIR = Path("data/metadata")

USER_AGENT = (
    "BoostRAG/0.2 source ingestion bot "
    "(automotive research assistant; local development)"
)

ECS_B58_CATEGORIES: dict[str, str] = {
    # Verify these URLs against https://www.ecstuning.com before running
    "intakes": "https://www.ecstuning.com/b-BMW/c-B58/s-Intake/",
    "downpipes": "https://www.ecstuning.com/b-BMW/c-B58/s-Downpipe/",
    "charge-pipes": "https://www.ecstuning.com/b-BMW/c-B58/s-Charge-Pipe/",
    "cooling": "https://www.ecstuning.com/b-BMW/c-B58/s-Cooling/",
    "exhausts": "https://www.ecstuning.com/b-BMW/c-B58/s-Exhaust/",
}

KNOWN_CHASSIS = {"G20", "G22", "G26", "G29", "G01", "G30", "G07", "F30", "F32", "F10"}


def get_ingested_urls() -> set[str]:
    """Return URLs already present in data/metadata/*.json."""
    urls: set[str] = set()
    for path in METADATA_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if url := data.get("url"):
                urls.add(url)
        except (json.JSONDecodeError, OSError):
            pass
    return urls
```

- [ ] **Step 3: Write failing tests for `get_ingested_urls()`**

Create `boostrag-api/tests/test_ecs_scraper.py`:

```python
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> BeautifulSoup:
    html = (FIXTURES / name).read_text(encoding="utf-8")
    return BeautifulSoup(html, "lxml")


# --- get_ingested_urls ---

def test_get_ingested_urls_returns_urls_from_metadata_jsons(tmp_path, monkeypatch):
    (tmp_path / "product_a.json").write_text(
        json.dumps({"url": "https://www.ecstuning.com/b-ecs/ES111/"}), encoding="utf-8"
    )
    (tmp_path / "product_b.json").write_text(
        json.dumps({"url": "https://www.ecstuning.com/b-ecs/ES222/"}), encoding="utf-8"
    )
    import ecs_scraper
    monkeypatch.setattr(ecs_scraper, "METADATA_DIR", tmp_path)
    result = ecs_scraper.get_ingested_urls()
    assert result == {
        "https://www.ecstuning.com/b-ecs/ES111/",
        "https://www.ecstuning.com/b-ecs/ES222/",
    }


def test_get_ingested_urls_ignores_malformed_json(tmp_path, monkeypatch):
    (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
    (tmp_path / "good.json").write_text(
        json.dumps({"url": "https://www.ecstuning.com/b-ecs/ES333/"}), encoding="utf-8"
    )
    import ecs_scraper
    monkeypatch.setattr(ecs_scraper, "METADATA_DIR", tmp_path)
    result = ecs_scraper.get_ingested_urls()
    assert result == {"https://www.ecstuning.com/b-ecs/ES333/"}


def test_get_ingested_urls_returns_empty_set_when_no_metadata(tmp_path, monkeypatch):
    import ecs_scraper
    monkeypatch.setattr(ecs_scraper, "METADATA_DIR", tmp_path)
    assert ecs_scraper.get_ingested_urls() == set()
```

- [ ] **Step 4: Run tests to confirm they fail**

```
pytest tests/test_ecs_scraper.py -v
```

Expected: ImportError because `ecs_scraper` is not importable yet (the file doesn't exist yet from pytest's perspective — run this before creating it if you want to see the failure; otherwise it should be 3 PASS after creating the file in Step 2).

If you created the file in Step 2 before running tests, run the tests now — they should pass.

- [ ] **Step 5: Confirm tests pass**

```
pytest tests/test_ecs_scraper.py -v
```

Expected: 3 PASS

- [ ] **Step 6: Commit**

```bash
git add boostrag-api/ecs_scraper.py boostrag-api/tests/test_ecs_scraper.py boostrag-api/tests/fixtures/
git commit -m "feat: add HTML fixtures and get_ingested_urls"
```

---

### Task 3: Implement `extract_ecs_price()`

**Files:**
- Modify: `boostrag-api/ecs_scraper.py`
- Modify: `boostrag-api/tests/test_ecs_scraper.py`

**Interfaces:**
- Consumes: `BeautifulSoup` parsed product page
- Produces: `extract_ecs_price(soup: BeautifulSoup) -> str` — base price like `"$349.00"`, or `"Unknown"` if not found

- [ ] **Step 1: Write failing tests**

Append to `boostrag-api/tests/test_ecs_scraper.py`:

```python
# --- extract_ecs_price ---

def test_extract_ecs_price_reads_json_ld_price():
    from ecs_scraper import extract_ecs_price
    soup = load_fixture("ecs_product_intake.html")
    assert extract_ecs_price(soup) == "$349.00"


def test_extract_ecs_price_falls_back_when_no_json_ld():
    from ecs_scraper import extract_ecs_price
    soup = load_fixture("ecs_product_downpipe.html")
    # No JSON-LD in downpipe fixture; regex should find $549.00, not $150.00 core deposit
    result = extract_ecs_price(soup)
    assert result == "$549.00"


def test_extract_ecs_price_returns_unknown_when_no_price():
    from ecs_scraper import extract_ecs_price
    soup = BeautifulSoup("<html><body><p>No price info here.</p></body></html>", "lxml")
    assert extract_ecs_price(soup) == "Unknown"
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_ecs_scraper.py::test_extract_ecs_price_reads_json_ld_price tests/test_ecs_scraper.py::test_extract_ecs_price_falls_back_when_no_json_ld tests/test_ecs_scraper.py::test_extract_ecs_price_returns_unknown_when_no_price -v
```

Expected: 3 FAIL — `cannot import name 'extract_ecs_price'`

- [ ] **Step 3: Implement `extract_ecs_price()` in `ecs_scraper.py`**

Append after `get_ingested_urls()`:

```python
def extract_ecs_price(soup: BeautifulSoup) -> str:
    """Extract base product price from JSON-LD structured data; fall back to regex."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            offers = data.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0]
            price = offers.get("price")
            currency = offers.get("priceCurrency", "USD")
            if price and currency == "USD":
                return f"${float(price):.2f}"
        except (json.JSONDecodeError, ValueError, AttributeError, IndexError):
            continue

    body_text = soup.get_text("\n", strip=True)
    return extract_price(body_text)
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/test_ecs_scraper.py::test_extract_ecs_price_reads_json_ld_price tests/test_ecs_scraper.py::test_extract_ecs_price_falls_back_when_no_json_ld tests/test_ecs_scraper.py::test_extract_ecs_price_returns_unknown_when_no_price -v
```

Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add boostrag-api/ecs_scraper.py boostrag-api/tests/test_ecs_scraper.py
git commit -m "feat: add extract_ecs_price with JSON-LD and regex fallback"
```

---

### Task 4: Implement `extract_fitment()`

**Files:**
- Modify: `boostrag-api/ecs_scraper.py`
- Modify: `boostrag-api/tests/test_ecs_scraper.py`

**Interfaces:**
- Consumes: `BeautifulSoup` parsed product page
- Produces: `extract_fitment(soup: BeautifulSoup) -> list[str]` — sorted list of chassis codes e.g. `["F30", "G01", "G20", "G29"]`, empty list if none found

- [ ] **Step 1: Write failing tests**

Append to `boostrag-api/tests/test_ecs_scraper.py`:

```python
# --- extract_fitment ---

def test_extract_fitment_returns_sorted_chassis_codes():
    from ecs_scraper import extract_fitment
    soup = load_fixture("ecs_product_intake.html")
    result = extract_fitment(soup)
    assert result == ["F30", "G01", "G20", "G29"]


def test_extract_fitment_returns_partial_list_when_fewer_chassis():
    from ecs_scraper import extract_fitment
    soup = load_fixture("ecs_product_downpipe.html")
    result = extract_fitment(soup)
    assert result == ["G20", "G26"]


def test_extract_fitment_returns_empty_list_when_no_chassis_found():
    from ecs_scraper import extract_fitment
    soup = BeautifulSoup("<html><body><p>No fitment info.</p></body></html>", "lxml")
    assert extract_fitment(soup) == []
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_ecs_scraper.py::test_extract_fitment_returns_sorted_chassis_codes tests/test_ecs_scraper.py::test_extract_fitment_returns_partial_list_when_fewer_chassis tests/test_ecs_scraper.py::test_extract_fitment_returns_empty_list_when_no_chassis_found -v
```

Expected: 3 FAIL — `cannot import name 'extract_fitment'`

- [ ] **Step 3: Implement `extract_fitment()` in `ecs_scraper.py`**

Append after `extract_ecs_price()`:

```python
_CHASSIS_PATTERN = re.compile(r'\b([FG]\d{2})\b')


def extract_fitment(soup: BeautifulSoup) -> list[str]:
    """Extract BMW chassis codes from anywhere in the page; filter to known B58 chassis."""
    found: set[str] = set()
    for code in _CHASSIS_PATTERN.findall(soup.get_text()):
        if code in KNOWN_CHASSIS:
            found.add(code)
    return sorted(found)
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/test_ecs_scraper.py::test_extract_fitment_returns_sorted_chassis_codes tests/test_ecs_scraper.py::test_extract_fitment_returns_partial_list_when_fewer_chassis tests/test_ecs_scraper.py::test_extract_fitment_returns_empty_list_when_no_chassis_found -v
```

Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add boostrag-api/ecs_scraper.py boostrag-api/tests/test_ecs_scraper.py
git commit -m "feat: add extract_fitment to detect BMW chassis codes"
```

---

### Task 5: Implement URL discovery (`_extract_product_urls_from_page`, `_get_next_page_url`, `get_product_urls`)

**Files:**
- Modify: `boostrag-api/ecs_scraper.py`
- Modify: `boostrag-api/tests/test_ecs_scraper.py`

**Interfaces:**
- Produces:
  - `_extract_product_urls_from_page(soup: BeautifulSoup, base_url: str) -> list[str]` — all ECS product URLs (containing `/ES\d+/`) found on the page, relative URLs resolved to absolute
  - `_get_next_page_url(soup: BeautifulSoup) -> str | None` — `href` of `<a rel="next">`, or `None`
  - `get_product_urls(category_url: str, session: requests.Session) -> list[str]` — crawls all pages in the category, returns deduplicated product URLs

- [ ] **Step 1: Write failing tests**

Append to `boostrag-api/tests/test_ecs_scraper.py`:

```python
# --- URL discovery ---

def test_extract_product_urls_from_page_finds_ecs_sku_links():
    from ecs_scraper import _extract_product_urls_from_page
    soup = load_fixture("ecs_category_page.html")
    urls = _extract_product_urls_from_page(soup, "https://www.ecstuning.com")
    assert "https://www.ecstuning.com/b-ecs-tuning/s-intake/ES4563456/" in urls
    assert "https://www.ecstuning.com/b-vrsf/s-charge-pipe/ES7891234/" in urls
    assert "https://www.ecstuning.com/b-ecs-tuning/s-heat-exchanger/ES1122334/" in urls
    assert len(urls) == 3


def test_get_next_page_url_returns_href_when_present():
    from ecs_scraper import _get_next_page_url
    soup = load_fixture("ecs_category_page.html")
    result = _get_next_page_url(soup)
    assert result == "https://www.ecstuning.com/b-BMW/c-B58/?page=2"


def test_get_next_page_url_returns_none_on_last_page():
    from ecs_scraper import _get_next_page_url
    soup = BeautifulSoup("<html><body><p>Last page, no next link.</p></body></html>", "lxml")
    assert _get_next_page_url(soup) is None


def test_get_product_urls_follows_pagination():
    from ecs_scraper import get_product_urls

    page1_html = (FIXTURES / "ecs_category_page.html").read_text(encoding="utf-8")
    page2_html = """
    <html><body>
      <a href="https://www.ecstuning.com/b-ecs/s-exhaust/ES9999999/">Exhaust</a>
    </body></html>
    """

    responses = {
        "https://www.ecstuning.com/b-BMW/c-B58/": page1_html,
        "https://www.ecstuning.com/b-BMW/c-B58/?page=2": page2_html,
    }

    mock_session = MagicMock()
    def fake_get(url, **kwargs):
        r = MagicMock()
        r.text = responses[url]
        r.raise_for_status = MagicMock()
        return r
    mock_session.get.side_effect = fake_get

    with patch("ecs_scraper.time.sleep"):
        urls = get_product_urls("https://www.ecstuning.com/b-BMW/c-B58/", mock_session)

    assert len(urls) == 4
    assert "https://www.ecstuning.com/b-ecs/s-exhaust/ES9999999/" in urls
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_ecs_scraper.py -k "product_url or next_page" -v
```

Expected: 4 FAIL — functions not defined yet.

- [ ] **Step 3: Implement the three functions in `ecs_scraper.py`**

Append after `extract_fitment()`:

```python
_ECS_SKU_RE = re.compile(r'/ES\d+/', re.IGNORECASE)


def _extract_product_urls_from_page(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Extract ECS product URLs (containing /ES<digits>/) from a parsed page."""
    urls: list[str] = []
    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        if _ECS_SKU_RE.search(href):
            if href.startswith("http"):
                urls.append(href)
            else:
                urls.append(base_url.rstrip("/") + "/" + href.lstrip("/"))
    return urls


def _get_next_page_url(soup: BeautifulSoup) -> str | None:
    """Return the href of <a rel='next'>, or None if on the last page."""
    tag = soup.find("a", rel="next")
    if tag and tag.get("href"):
        return tag["href"]
    return None


def get_product_urls(category_url: str, session: requests.Session) -> list[str]:
    """Crawl a category URL with pagination and return all discovered product URLs."""
    base_url = "/".join(category_url.split("/")[:3])  # https://www.ecstuning.com
    all_urls: list[str] = []
    current_url: str | None = category_url

    while current_url:
        response = session.get(
            current_url, headers={"User-Agent": USER_AGENT}, timeout=20
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        all_urls.extend(_extract_product_urls_from_page(soup, base_url))
        current_url = _get_next_page_url(soup)
        if current_url:
            time.sleep(1.5)

    return list(dict.fromkeys(all_urls))  # deduplicate, preserve order
```

- [ ] **Step 4: Run URL discovery tests to confirm they pass**

```
pytest tests/test_ecs_scraper.py -k "product_url or next_page" -v
```

Expected: 4 PASS

- [ ] **Step 5: Run full suite to catch regressions**

```
pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add boostrag-api/ecs_scraper.py boostrag-api/tests/test_ecs_scraper.py
git commit -m "feat: add ECS category page crawler with pagination"
```

---

### Task 6: Implement `scrape_ecs_b58()` orchestrator and `main()` CLI

**Files:**
- Modify: `boostrag-api/ecs_scraper.py`
- Modify: `boostrag-api/tests/test_ecs_scraper.py`

**Interfaces:**
- Consumes: all functions from Tasks 2–5, plus `ingest_url(url, *, fitment, price_override)` from Task 1
- Produces: `scrape_ecs_b58(category_urls, *, limit, force, dry_run)` and `main()` CLI entry point

- [ ] **Step 1: Write failing tests**

Append to `boostrag-api/tests/test_ecs_scraper.py`:

```python
# --- scrape_ecs_b58 orchestrator ---

def _make_orchestrator_mocks(monkeypatch, discovered_urls, already_ingested):
    """Shared setup: mock all I/O-touching functions for orchestrator tests."""
    import ecs_scraper

    monkeypatch.setattr(
        ecs_scraper, "get_product_urls", lambda url, session: discovered_urls
    )
    monkeypatch.setattr(
        ecs_scraper, "get_ingested_urls", lambda: already_ingested
    )
    monkeypatch.setattr(ecs_scraper, "extract_ecs_price", lambda soup: "$299.00")
    monkeypatch.setattr(ecs_scraper, "extract_fitment", lambda soup: ["G20"])


def test_scrape_ecs_b58_skips_already_ingested_urls(tmp_path, monkeypatch):
    import ecs_scraper

    _make_orchestrator_mocks(
        monkeypatch,
        discovered_urls=[
            "https://www.ecstuning.com/b-ecs/ES111/",
            "https://www.ecstuning.com/b-ecs/ES222/",
        ],
        already_ingested={"https://www.ecstuning.com/b-ecs/ES111/"},
    )

    mock_session = MagicMock()
    mock_session.get.return_value.text = "<html><body></body></html>"

    ingested = []
    def fake_ingest(url, **kwargs):
        ingested.append(url)
        return (tmp_path / "f.txt", tmp_path / "f.json", {"url": url, "route": "cleaned"})

    with patch("ecs_scraper.ingest_url", side_effect=fake_ingest):
        with patch("ecs_scraper.requests.Session", return_value=mock_session):
            with patch("ecs_scraper._check_robots"):
                with patch("ecs_scraper.time.sleep"):
                    ecs_scraper.scrape_ecs_b58(
                        ["https://www.ecstuning.com/b-BMW/c-B58/"],
                        limit=None, force=False, dry_run=False,
                    )

    assert ingested == ["https://www.ecstuning.com/b-ecs/ES222/"]


def test_scrape_ecs_b58_force_flag_reingest_known_url(tmp_path, monkeypatch):
    import ecs_scraper

    _make_orchestrator_mocks(
        monkeypatch,
        discovered_urls=["https://www.ecstuning.com/b-ecs/ES111/"],
        already_ingested={"https://www.ecstuning.com/b-ecs/ES111/"},
    )

    mock_session = MagicMock()
    mock_session.get.return_value.text = "<html><body></body></html>"

    ingested = []
    def fake_ingest(url, **kwargs):
        ingested.append(url)
        return (tmp_path / "f.txt", tmp_path / "f.json", {"url": url, "route": "cleaned"})

    with patch("ecs_scraper.ingest_url", side_effect=fake_ingest):
        with patch("ecs_scraper.requests.Session", return_value=mock_session):
            with patch("ecs_scraper._check_robots"):
                with patch("ecs_scraper.time.sleep"):
                    ecs_scraper.scrape_ecs_b58(
                        ["https://www.ecstuning.com/b-BMW/c-B58/"],
                        limit=None, force=True, dry_run=False,
                    )

    assert ingested == ["https://www.ecstuning.com/b-ecs/ES111/"]


def test_scrape_ecs_b58_dry_run_does_not_call_ingest(monkeypatch):
    import ecs_scraper

    _make_orchestrator_mocks(
        monkeypatch,
        discovered_urls=["https://www.ecstuning.com/b-ecs/ES111/"],
        already_ingested=set(),
    )

    with patch("ecs_scraper.ingest_url") as mock_ingest:
        with patch("ecs_scraper.requests.Session"):
            with patch("ecs_scraper._check_robots"):
                with patch("ecs_scraper.time.sleep"):
                    ecs_scraper.scrape_ecs_b58(
                        ["https://www.ecstuning.com/b-BMW/c-B58/"],
                        limit=None, force=False, dry_run=True,
                    )

    mock_ingest.assert_not_called()


def test_scrape_ecs_b58_limit_caps_ingestion(tmp_path, monkeypatch):
    import ecs_scraper

    _make_orchestrator_mocks(
        monkeypatch,
        discovered_urls=[f"https://www.ecstuning.com/b-ecs/ES{i:06d}/" for i in range(10)],
        already_ingested=set(),
    )

    mock_session = MagicMock()
    mock_session.get.return_value.text = "<html><body></body></html>"

    ingested = []
    def fake_ingest(url, **kwargs):
        ingested.append(url)
        return (tmp_path / "f.txt", tmp_path / "f.json", {"url": url, "route": "cleaned"})

    with patch("ecs_scraper.ingest_url", side_effect=fake_ingest):
        with patch("ecs_scraper.requests.Session", return_value=mock_session):
            with patch("ecs_scraper._check_robots"):
                with patch("ecs_scraper.time.sleep"):
                    ecs_scraper.scrape_ecs_b58(
                        ["https://www.ecstuning.com/b-BMW/c-B58/"],
                        limit=3, force=False, dry_run=False,
                    )

    assert len(ingested) == 3
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_ecs_scraper.py -k "scrape_ecs" -v
```

Expected: 4 FAIL — `scrape_ecs_b58` not defined.

- [ ] **Step 3: Implement `_check_robots()`, `scrape_ecs_b58()`, and `main()` in `ecs_scraper.py`**

Append to `ecs_scraper.py`:

```python
def _check_robots(session: requests.Session) -> None:
    """Abort if robots.txt disallows crawling ECS Tuning product pages."""
    rp = urllib.robotparser.RobotFileParser()
    try:
        response = session.get(
            "https://www.ecstuning.com/robots.txt",
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        rp.parse(response.text.splitlines())
    except requests.RequestException:
        print("Warning: could not fetch robots.txt — proceeding with caution.")
        return

    if not rp.can_fetch(USER_AGENT, "https://www.ecstuning.com/b-BMW/"):
        raise RuntimeError("robots.txt disallows crawling ECS Tuning. Aborting.")


def scrape_ecs_b58(
    category_urls: list[str],
    *,
    limit: int | None,
    force: bool,
    dry_run: bool,
) -> None:
    session = requests.Session()
    _check_robots(session)

    already_ingested = set() if force else get_ingested_urls()

    all_product_urls: list[str] = []
    for cat_url in category_urls:
        print(f"Discovering: {cat_url}")
        found = get_product_urls(cat_url, session)
        print(f"  Found {len(found)} product URLs")
        all_product_urls.extend(found)
        time.sleep(1.5)

    new_urls = [u for u in dict.fromkeys(all_product_urls) if u not in already_ingested]
    if limit is not None:
        new_urls = new_urls[:limit]

    print(f"\n{len(new_urls)} new products to ingest (force={force}, dry_run={dry_run})\n")

    for url in new_urls:
        if dry_run:
            print(f"[dry-run] Would ingest: {url}")
            continue

        try:
            response = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            price = extract_ecs_price(soup)
            raw_fitment = extract_fitment(soup)
            fitment = raw_fitment if raw_fitment else None

            _, _, metadata = ingest_url(url, fitment=fitment, price_override=price)
            print(
                f"Ingested: {url}\n"
                f"  Route: {metadata.get('route')} | "
                f"Price: {price} | Fitment: {fitment}"
            )
        except Exception as exc:
            print(f"Failed: {url} — {exc}")

        time.sleep(1.5)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape ECS Tuning B58 product pages into the BoostRAG corpus."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-scrape and overwrite already-ingested URLs.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be ingested without writing anything.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Stop after ingesting N products.",
    )
    parser.add_argument(
        "--category",
        choices=list(ECS_B58_CATEGORIES.keys()),
        default=None,
        help="Scrape a single category only.",
    )
    args = parser.parse_args()

    category_urls = (
        [ECS_B58_CATEGORIES[args.category]]
        if args.category
        else list(ECS_B58_CATEGORIES.values())
    )

    scrape_ecs_b58(category_urls, limit=args.limit, force=args.force, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run orchestrator tests to confirm they pass**

```
pytest tests/test_ecs_scraper.py -k "scrape_ecs" -v
```

Expected: 4 PASS

- [ ] **Step 5: Run the full test suite**

```
pytest tests/ -v
```

Expected: all tests PASS. Count should be 17 total (4 from `test_ingest_extensions.py` + 13 from `test_ecs_scraper.py`).

- [ ] **Step 6: Commit**

```bash
git add boostrag-api/ecs_scraper.py boostrag-api/tests/test_ecs_scraper.py
git commit -m "feat: add scrape_ecs_b58 orchestrator and CLI"
```

---

## Post-Implementation Checklist

After all tasks are green, do these before scaling up:

1. **Verify ECS category URLs** — Visit each URL in `ECS_B58_CATEGORIES` in a browser. Confirm they load product listings. Update the dict if structure differs.

2. **Verify fixture HTML against the live site** — Open a real ECS product page, view source, and confirm:
   - `<script type="application/ld+json">` contains `offers.price`
   - Chassis codes appear in parentheses like `(G20)` somewhere on the page
   - Product links contain `/ES\d+/`
   Update fixtures if ECS's actual HTML differs, then re-run tests.

3. **Dry-run first**:
   ```bash
   cd boostrag-api
   python ecs_scraper.py --dry-run --limit 5
   ```
   Confirm it discovers URLs without writing anything.

4. **Small batch inspection**:
   ```bash
   python ecs_scraper.py --limit 20 --category intakes
   ```
   Open 3–4 files in `data/cleaned/` and verify Brand, Category, Price, and Fitment look correct. Check `data/metadata/` JSON for the same.

5. **Rebuild ChromaDB after a satisfactory batch**:
   ```bash
   python chunk_embed.py
   ```
