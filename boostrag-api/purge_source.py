from __future__ import annotations

import argparse
import json
from pathlib import Path

import chromadb

from provenance import add_to_blacklist
from retrieve import CHROMA_PATH, COLLECTION_NAME

METADATA_DIR = Path("data/metadata")


def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_collection(name=COLLECTION_NAME)


def purge_source(url: str, *, collection=None) -> dict:
    """Remove a source's chunks + files and blacklist it so it can't be re-ingested."""
    if collection is None:
        collection = _get_collection()

    # 1. delete chunks whose metadata url matches
    collection.delete(where={"url": url})

    # 2. delete cleaned text + metadata files that reference this url
    files_deleted = 0
    for meta_path in METADATA_DIR.glob("*.json"):
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("url") == url:
            text_file = data.get("text_file")
            if text_file and Path(text_file).exists():
                Path(text_file).unlink()
                files_deleted += 1
            meta_path.unlink()
            files_deleted += 1

    # 3. blacklist
    add_to_blacklist(url)

    return {"blacklisted": True, "chunks_deleted": True, "files_deleted": files_deleted}


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge and blacklist a bad source URL.")
    parser.add_argument("url", help="The source URL to purge and ban.")
    args = parser.parse_args()
    result = purge_source(args.url)
    print(f"Purged {args.url}: {result}")


if __name__ == "__main__":
    main()
