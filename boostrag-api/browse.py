from __future__ import annotations

from storage import DATA_DIR
from preprocess import load_documents
from source_ranker import tier_for_url

CLEANED_DIR = DATA_DIR / "cleaned"

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
    """Return cleaned corpus items for a category slug, or None if unknown."""
    if slug not in CATEGORY_SLUGS:
        return None
    wanted = CATEGORY_SLUGS[slug]

    items: list[dict] = []
    if CLEANED_DIR.exists():
        for doc in load_documents(CLEANED_DIR):
            if wanted is not None and doc.get("category") not in wanted:
                continue
            url = doc.get("url") or doc.get("source_url")
            items.append({
                "product": doc.get("product") or doc.get("source_title"),
                "brand": doc.get("brand"),
                "price": doc.get("price"),
                "url": url,
                "trust_tier": doc.get("trust_tier") or (tier_for_url(url) if url else None),
                "text_preview": (doc.get("text") or "")[:250],
            })
    return {"category": slug, "count": len(items), "items": items}
