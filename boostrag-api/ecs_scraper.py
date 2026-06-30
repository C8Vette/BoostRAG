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
