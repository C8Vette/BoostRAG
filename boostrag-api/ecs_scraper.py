from __future__ import annotations

import argparse
import json
import re
import time
import urllib.robotparser
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from ingest_urls import ingest_url, extract_price

METADATA_DIR = Path("data/metadata")

USER_AGENT = (
    "BoostRAG/0.2 source ingestion bot "
    "(automotive research assistant; local development)"
)

# Vehicle-specific category entry points. Each URL should be a paginated
# product listing for the target vehicle on ecstuning.com.
ECS_B58_CATEGORIES: dict[str, str] = {
    "m340i-xdrive": "https://www.ecstuning.com/BMW-G20-M340i_xDrive-B58_3.0L/",
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


_CHASSIS_PATTERN = re.compile(r'\b([FG]\d{2})\b')


def extract_fitment(soup: BeautifulSoup) -> list[str]:
    """Extract BMW chassis codes from anywhere in the page; filter to known B58 chassis."""
    found: set[str] = set()
    for code in _CHASSIS_PATTERN.findall(soup.get_text()):
        if code in KNOWN_CHASSIS:
            found.add(code)
    return sorted(found)


# Matches ECS product page URLs: /b-{brand}/{product-name}/{sku}/
_ECS_PRODUCT_RE = re.compile(r'/b-[^/]+/[^/]+/[^/]+/', re.IGNORECASE)


def _extract_product_urls_from_page(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Extract ECS product URLs from a parsed page."""
    urls: list[str] = []
    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        if _ECS_PRODUCT_RE.search(href):
            if href.startswith("http"):
                urls.append(href)
            else:
                urls.append(urljoin(base_url, href))
    return urls


def _get_next_page_url(soup: BeautifulSoup) -> str | None:
    """Return the href of <a rel='next'>, or None if on the last page."""
    tag = soup.find("a", rel="next")
    if tag and tag.get("href"):
        return tag["href"]
    return None


def _fetch_page_html(page, url: str) -> str:
    """Navigate to URL with Playwright and return fully-rendered HTML."""
    page.goto(url, wait_until="networkidle", timeout=60000)
    return page.content()


def get_product_urls(category_url: str, fetch_fn: Callable[[str], str]) -> list[str]:
    """Crawl a category URL with pagination and return all discovered product URLs."""
    base_url = "https://www.ecstuning.com"
    all_urls: list[str] = []
    current_url: str | None = category_url

    while current_url:
        html = fetch_fn(current_url)
        soup = BeautifulSoup(html, "lxml")
        all_urls.extend(_extract_product_urls_from_page(soup, base_url))
        next_href = _get_next_page_url(soup)
        current_url = urljoin(current_url, next_href) if next_href else None
        if current_url:
            time.sleep(1.5)

    return list(dict.fromkeys(all_urls))  # deduplicate, preserve order


def _check_robots() -> None:
    """Abort if robots.txt disallows crawling ECS Tuning product pages."""
    rp = urllib.robotparser.RobotFileParser()
    try:
        response = requests.get(
            "https://www.ecstuning.com/robots.txt",
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        response.raise_for_status()
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
    _check_robots()

    already_ingested = set() if force else get_ingested_urls()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(user_agent=USER_AGENT).new_page()

        try:
            fetch_fn: Callable[[str], str] = lambda url: _fetch_page_html(page, url)

            all_product_urls: list[str] = []
            for cat_url in category_urls:
                print(f"Discovering: {cat_url}")
                try:
                    found = get_product_urls(cat_url, fetch_fn)
                    print(f"  Found {len(found)} product URLs")
                    all_product_urls.extend(found)
                except Exception as exc:
                    print(f"  Failed to crawl {cat_url}: {exc} — skipping")
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
                    html = _fetch_page_html(page, url)
                    soup = BeautifulSoup(html, "lxml")

                    price = extract_ecs_price(soup)
                    raw_fitment = extract_fitment(soup)
                    fitment = raw_fitment if raw_fitment else None

                    _, _, metadata = ingest_url(
                        url, fitment=fitment, price_override=price, prefetched_html=html
                    )
                    print(
                        f"Ingested: {url}\n"
                        f"  Route: {metadata.get('route')} | "
                        f"Price: {price} | Fitment: {fitment}"
                    )
                except Exception as exc:
                    print(f"Failed: {url} — {exc}")

                time.sleep(1.5)
        finally:
            browser.close()


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
