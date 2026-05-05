from __future__ import annotations

import os
from typing import Dict, List

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

from preprocess import load_documents


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBED_MODEL = "text-embedding-3-small"
CHROMA_PATH = "vectorstore/chroma_db"
COLLECTION_NAME = "boostrag_docs"

client = OpenAI(api_key=OPENAI_API_KEY)


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> List[str]:
    """
    Split a document into overlapping chunks for embedding.

    The overlap helps to maintain context across chunks.

    Args:
        text: The full text of the document to be chunked.
        chunk_size: The maximum number of characters in each chunk.
        overlap: The number of characters to overlap between consecutive chunks.

    Returns:
        A list of text chunks derived from the original document.
    """
    if not text.strip():
        return []

    chunks: List[str] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == text_length:
            break
        start = end - overlap

    return chunks


def build_chunk_records(documents: List[Dict[str, str]]) -> List[Dict]:
    """
    Convert documents into chunk records with metadata.

    Each record corresponds to a chunk of text and includes:
        - a unique ID
        - the chunk text
        - document metadata

    Args:
        documents: A list of document dictionaries, each containing metadata and text.

    Returns:
        A list of chunk records ready for embedding and storage.
    """
    records: List[Dict] = []

    for doc_idx, doc in enumerate(documents):
        chunks = chunk_text(doc["text"])
        for chunk_idx, chunk in enumerate(chunks):
            records.append(
                {
                    "id": f"{doc_idx}_{chunk_idx}",
                    "text": chunk,
                    "metadata": {
                        "brand": doc.get("brand", ""),
                        "category": doc.get("category", ""),
                        "product": doc.get("product", ""),
                        "vehicle": doc.get("vehicle", ""),
                        "source_type": doc.get("source_type", ""),
                        "url": doc.get("url", ""),
                        "price": doc.get("price", ""),
                        "source_file": doc.get("source_file", ""),
                        "chunk_index": chunk_idx,
                    },
                }
            )
    return records


def get_embedding(text: str) -> List[float]:
    """
    Generate an embedding vector for the given text using OpenAI's API.
    
    Args:
        text: Chunk text for embedding.
        
    Returns:
        A list of floats representing the embedding vector.
    """
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=text,
    )
    return response.data[0].embedding


def store_in_chroma(records: List[Dict]) -> None:
    """
    Store chunk records in a Chroma vector database.
    
    This function creates or retrieves a Chroma collection, generates the embeddings
    for each chunk, and upserts the data into the collection.
    
    Args:
        records: A list of chunk records, each containing an ID, text, and metadata.
    """
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)

    ids = []
    documents = []
    metadatas = []
    embeddings = []

    for record in records:
        ids.append(record["id"])
        documents.append(record["text"])
        metadatas.append(record["metadata"])
        embeddings.append(get_embedding(record["text"]))

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )

# This function is strictly to help for the DEPLOYED Streamlit app, which needs to 
# ensure that there is a chroma collection with data in it before taking questions
def ensure_chroma_collection() -> None:
    """
    Ensure the BoostRAG Chroma collection exists.

    If the collection does not exist yet, load the cleaned corpus,
    build chunk records, and store them in Chroma.
    """
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

    try:
        chroma_client.get_collection(name=COLLECTION_NAME)
    except Exception:
        docs = load_documents()
        chunk_records = build_chunk_records(docs)
        store_in_chroma(chunk_records)

if __name__ == "__main__":
    docs = load_documents()
    print(f"Loaded {len(docs)} documents.")

    chunk_records = build_chunk_records(docs)
    print(f"Built {len(chunk_records)} chunks.")

    store_in_chroma(chunk_records)
    print("Stored chunks in Chroma successfully.")