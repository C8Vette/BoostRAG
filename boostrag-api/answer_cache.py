from __future__ import annotations

import json
import os
import time
from pathlib import Path

from storage import DATA_DIR

CACHE_PATH = DATA_DIR / "cache" / "answers.json"


def _normalize(query: str) -> str:
    return " ".join(query.lower().split())


def _load() -> dict:
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def get_cached(query: str) -> dict | None:
    ttl_seconds = float(os.getenv("CACHE_TTL_HOURS", "24")) * 3600
    entry = _load().get(_normalize(query))
    if not entry:
        return None
    if time.time() - entry["ts"] > ttl_seconds:
        return None
    return entry["result"]


def set_cached(query: str, result: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = _load()
    data[_normalize(query)] = {"ts": time.time(), "result": result}
    CACHE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
