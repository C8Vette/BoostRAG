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
