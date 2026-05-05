from __future__ import annotations

import os
from typing import List, Dict

import chromadb
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBED_MODEL = "text-embedding-3-small"
CHROMA_PATH = "vectorstore/chroma_db"
COLLECTION_NAME = "boostrag_docs"

client = OpenAI(api_key=OPENAI_API_KEY)


def get_query_embedding(query: str) -> List[float]:
    """
    Generate an embedding vector for the user's query using OpenAI's API.
    
    Args:
        query: The user's input question for retrieval.

    Returns:
        Query embedding vector as a list of floats.
    """
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=query,
    )
    return response.data[0].embedding


def retrieve_chunks(query: str, top_k: int = 3) -> List[Dict]:
    """
    Retrieve the most relevant chunks from the Chroma vector database based on the query embedding.
    
    Args:
        query: The user's input question for retrieval.
        top_k: The number of top relevant chunks to retrieve.
        
    Returns:
        A list of dictionaries, each containing the retrieved chunk's text, metadata, and distance score.
    """
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_collection(name=COLLECTION_NAME)

    query_embedding = get_query_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    output: List[Dict] = []

    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc_id, doc_text, meta, distance in zip(ids, docs, metas, distances):
        output.append(
            {
                "id": doc_id,
                "text": doc_text,
                "metadata": meta,
                "distance": distance,
            }
        )

    return output


if __name__ == "__main__":
    user_query = input("Enter your query: ").strip()
    matches = retrieve_chunks(user_query, top_k=3)

    print("\nTop matches:\n")
    for i, match in enumerate(matches, start=1):
        print(f"[{i}] Source: {match['metadata'].get('source_file', 'unknown')}")
        print(f"Category: {match['metadata'].get('category', 'N/A')}")
        print(f"Product: {match['metadata'].get('product', 'N/A')}")
        print(f"Distance: {match['distance']}")
        print(match["text"][:500])
        print("-" * 80)