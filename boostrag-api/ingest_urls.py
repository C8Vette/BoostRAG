from __future__ import annotations

import argparse
import json
import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from source_ranker import score_source


DATA_DIR = Path("data")
CLEANED_DIR = DATA_DIR / "cleaned"
LIMITED_DIR = DATA_DIR / "limited"
QUARANTINE_DIR = DATA_DIR / "quarantine"
METADATA_DIR = DATA_DIR / "metadata"

BRAND_KEYWORDS = {
    "vrsf": "VRSF",
    "active autowerke": "Active Autowerke",
    "dinan": "Dinan",
    "cts turbo": "CTS Turbo",
    "burger motorsports": "Burger Motorsports",
    "bms": "Burger Motorsports",
    "mhd": "MHD",
    "bootmod3": "bootmod3",
    "bm3": "bootmod3",
    "turner": "Turner Motorsport",
    "ecs": "ECS Tuning",
    "bilstein": "Bilstein",
    "pure turbos": "Pure Turbos",
    "pure800": "Pure Turbos",
    "pure 800": "Pure Turbos",
    "kies": "Kies Motorsports",
}

CATEGORY_KEYWORDS = {
    "turbo upgrade components": "Turbo",
    "pure800": "Turbo",
    "pure 800": "Turbo",
    "turbo upgrade": "Turbo",
    "downpipe": "Downpipe",
    "intake": "Intake",
    "charge pipe": "Charge Pipe",
    "intercooler": "Cooling",
    "heat exchanger": "Cooling",
    "cooling": "Cooling",
    "turbo inlet": "Turbo Inlet",
    "turbo": "Turbo",
    "tune": "Tuning",
    "tuning": "Tuning",
    "flash": "Tuning",
    "suspension": "Suspension",
    "coilover": "Suspension",
    "spring": "Suspension",
    "brake": "Braking",
    "rotor": "Braking",
    "pad": "Braking",
    "wheel": "Wheels & Tires",
    "tire": "Wheels & Tires",
    "exhaust": "Exhaust",
}


def normalize_domain(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def slugify(value: str, max_length: int = 90) -> str:
    value = value.lower().strip()
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value[:max_length] or "source"


def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": (
            "BoostRAG/0.2 source ingestion bot "
            "(automotive research assistant; local development)"
        )
    }

    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()

    return response.text


def clean_soup(soup: BeautifulSoup) -> None:
    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "nav",
            "footer",
            "iframe",
            "form",
            "button",
        ]
    ):
        tag.decompose()


def extract_title(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    if h1:
        h1_text = h1.get_text(" ", strip=True)
        if h1_text:
            return h1_text

    if soup.title and soup.title.string:
        return soup.title.string.strip()

    return "Untitled Source"


def extract_meta_description(soup: BeautifulSoup) -> str | None:
    tag = soup.find("meta", attrs={"name": "description"})
    if tag and tag.get("content"):
        return tag["content"].strip()

    og = soup.find("meta", attrs={"property": "og:description"})
    if og and og.get("content"):
        return og["content"].strip()

    return None


def extract_main_text(soup: BeautifulSoup) -> str:
    candidates = []

    selectors = [
        "main",
        "article",
        "[role='main']",
        ".product-details",
        ".product-description",
        ".description",
        "#description",
        ".tab-content",
    ]

    for selector in selectors:
        found = soup.select_one(selector)
        if found:
            candidates.append(found.get_text("\n", strip=True))

    if not candidates and soup.body:
        candidates.append(soup.body.get_text("\n", strip=True))

    text = "\n".join(candidates)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    lines = []
    seen = set()

    for line in text.splitlines():
        clean_line = line.strip()

        if not clean_line:
            continue

        lowered = clean_line.lower()

        if lowered in seen:
            continue

        if len(clean_line) < 3:
            continue

        seen.add(lowered)
        lines.append(clean_line)

    return "\n".join(lines)


def guess_brand(text: str, title: str, domain: str) -> str:
    haystack = f"{title}\n{text}\n{domain}".lower()

    for keyword, brand in BRAND_KEYWORDS.items():
        if keyword in haystack:
            return brand

    if "ecs" in domain:
        return "ECS Tuning"

    if "turner" in domain:
        return "Turner Motorsport"

    return "Unknown"


def guess_category(text: str, title: str) -> str:
    haystack = f"{title}\n{text}".lower()

    for keyword, category in CATEGORY_KEYWORDS.items():
        if keyword in haystack:
            return category

    return "Unknown"


def guess_vehicle(text: str, title: str) -> str:
    haystack = f"{title}\n{text}".lower()

    if "m340i" in haystack or "g20" in haystack:
        return "BMW M340i G20"

    if "m440i" in haystack or "g22" in haystack:
        return "BMW M440i G22"

    if "b58" in haystack:
        return "BMW B58"

    return "Unknown"


def extract_price(text: str) -> str:
    """
    Extract the most likely primary product price.

    This avoids grabbing option add-ons like:
    '(+ $1800)' or refundable core deposits before the actual product price.
    """
    # Prefer explicit USD product-price formatting.
    usd_matches = re.findall(
        r"\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s?USD",
        text,
        flags=re.IGNORECASE,
    )

    if usd_matches:
        return usd_matches[0].strip()

    # Prefer prices near common product-price labels.
    labeled_match = re.search(
        r"(?:price|unit price|subtotal)\s*:?\s*(\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
        text,
        flags=re.IGNORECASE,
    )

    if labeled_match:
        return labeled_match.group(1).strip()

    # Avoid add-on prices written like '(+ $1800)'.
    all_matches = re.findall(
        r"(?<!\+\s)\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?",
        text,
    )

    if not all_matches:
        return "Unknown"

    return all_matches[0].strip()

def route_to_directory(route: str) -> Path:
    if route == "cleaned":
        return CLEANED_DIR

    if route == "limited":
        return LIMITED_DIR

    return QUARANTINE_DIR


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
) -> str:
    claim_types = ", ".join(score["claim_types"])
    risk_flags = ", ".join(score["risk_flags"]) if score["risk_flags"] else "None"

    metadata_header = f"""
    Source Title: {title}
    Source URL: {url}
    Source Domain: {domain}
    Brand: {brand}
    Category: {category}
    Vehicle: {vehicle}
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


def ingest_url(url: str) -> tuple[Path, Path, dict]:
    for directory in [CLEANED_DIR, LIMITED_DIR, QUARANTINE_DIR, METADATA_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")
    clean_soup(soup)

    title = extract_title(soup)
    description = extract_meta_description(soup)
    body_text = extract_main_text(soup)
    domain = normalize_domain(url)

    if len(body_text) < 300:
        raise ValueError(
            "Extracted text is very short. The page may require JavaScript, "
            "block scraping, or lack useful page content."
        )

    brand = guess_brand(body_text, title, domain)
    category = guess_category(body_text, title)
    vehicle = guess_vehicle(body_text, title)
    price = extract_price(body_text)

    score = score_source(url=url, title=title, text=body_text).to_dict()

    output_dir = route_to_directory(score["route"])

    filename_base = slugify(f"{brand}_{category}_{title}")
    txt_path = output_dir / f"{filename_base}.txt"
    json_path = METADATA_DIR / f"{filename_base}.json"

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
    )

    metadata = {
        "title": title,
        "url": url,
        "domain": domain,
        "description": description,
        "brand": brand,
        "category": category,
        "vehicle": vehicle,
        "price": price,
        **score,
        "text_file": str(txt_path),
        "metadata_file": str(json_path),
        "date_ingested": datetime.now(timezone.utc).isoformat(),
    }

    txt_path.write_text(cleaned_text, encoding="utf-8")
    json_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return txt_path, json_path, metadata


def read_urls_from_file(path: Path) -> list[str]:
    urls = []

    for line in path.read_text(encoding="utf-8").splitlines():
        clean_line = line.strip()

        if not clean_line or clean_line.startswith("#"):
            continue

        urls.append(clean_line)

    return urls


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest and trust-score web URLs into BoostRAG."
    )

    parser.add_argument(
        "inputs",
        nargs="+",
        help="One or more URLs, or paths to .txt files containing URLs.",
    )

    args = parser.parse_args()

    urls: list[str] = []

    for item in args.inputs:
        path = Path(item)

        if path.exists() and path.suffix.lower() == ".txt":
            urls.extend(read_urls_from_file(path))
        else:
            urls.append(item)

    for url in urls:
        print(f"\nIngesting: {url}")

        try:
            txt_path, json_path, metadata = ingest_url(url)

            print(f"Saved text: {txt_path}")
            print(f"Saved metadata: {json_path}")
            print(f"Route: {metadata['route']}")
            print(f"Trust tier: {metadata['trust_tier']}")
            print(f"Review status: {metadata['review_status']}")
            print(f"Claim types: {', '.join(metadata['claim_types'])}")
            print(
                "Risk flags: "
                + (", ".join(metadata["risk_flags"]) if metadata["risk_flags"] else "None")
            )
            print(f"Reason: {metadata['reason']}")

        except Exception as exc:
            print(f"Failed to ingest {url}: {exc}")


if __name__ == "__main__":
    main()
