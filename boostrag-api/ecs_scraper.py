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
