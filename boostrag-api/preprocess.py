from __future__ import annotations

from pathlib import Path
from typing import Dict, List

# Directory for collecting cleaned corpus files for the RAG pipeline
DATA_DIR = Path("data/cleaned")


def parse_document(file_path: Path) -> Dict[str, str]:
    """
    Parse a cleaned corpus .txt file with metadata headers followed by body text.

    Expected format:
        Brand: ...
        Category: ...
        Product: ...
        Vehicle: ...
        Source Type: ...
        URL: ...
        Price: ...

        A blank line separates the metadata from the body text, which can be multiple lines.
        The returned dictionary includes all parsed metadata as well as:
            - source_file: Original filename
            - text: The full body text content of the document
        Summary:
        ...
    """
    raw_text = file_path.read_text(encoding="utf-8").strip()
    lines = raw_text.splitlines()

    metadata: Dict[str, str] = {}
    body_lines: List[str] = []

    in_body = False
    for line in lines:
        stripped = line.strip()

        # An empty line indicates the end of metadata and the start of body text
        if not stripped and not in_body:
            in_body = True
            continue

        # Parse metadata lines until we hit the first empty line
        if not in_body and ":" in stripped:
            key, value = stripped.split(":", 1)
            metadata[key.strip().lower().replace(" ", "_")] = value.strip()
        else:
            in_body = True
            body_lines.append(line)

    body_text = "\n".join(body_lines).strip()

    metadata["source_file"] = file_path.name
    metadata["text"] = body_text
    return metadata


def load_documents(data_dir: Path = DATA_DIR) -> List[Dict[str, str]]:
    """
    Load all .txt files from the cleaned corpus directory.

    Args:
        data_dir: Path to the directory containing cleaned .txt files.

    Returns:
        A list of dictionaries, each containing metadata and text for a document.

    Raises:
        FileNotFoundError: If the specified data directory does not exist.
    """
    if not data_dir.exists():
        raise FileNotFoundError(f"Directory not found: {data_dir}")

    docs: List[Dict[str, str]] = []
    for file_path in sorted(data_dir.glob("*.txt")):
        docs.append(parse_document(file_path))

    return docs


if __name__ == "__main__":
    documents = load_documents()
    print(f"Loaded {len(documents)} documents.\n")

    for doc in documents:
        print(f"FILE: {doc.get('source_file', 'unknown')}")
        print(f"BRAND: {doc.get('brand', 'N/A')}")
        print(f"CATEGORY: {doc.get('category', 'N/A')}")
        print(f"PRODUCT: {doc.get('product', 'N/A')}")
        preview = doc.get("text", "")[:250].replace("\n", " ")
        print(f"PREVIEW: {preview}...")
        print("-" * 60)