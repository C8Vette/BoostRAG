from __future__ import annotations

import os
from pathlib import Path

# Root for all mutable storage. Local default preserves the historical repo
# layout (data/ and vectorstore/ under boostrag-api/). In production set
# BOOSTRAG_DATA_DIR to a mounted persistent disk so state survives restarts.
STORAGE_ROOT = Path(os.getenv("BOOSTRAG_DATA_DIR", "."))

DATA_DIR = STORAGE_ROOT / "data"
CHROMA_PATH = str(STORAGE_ROOT / "vectorstore" / "chroma_db")
COLLECTION_NAME = "boostrag_docs"
