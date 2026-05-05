from __future__ import annotations

import os
from typing import List, Dict

from dotenv import load_dotenv
from openai import OpenAI

from retrieve import retrieve_chunks


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is missing. Add it to boostrag-api/.env."
    )
GEN_MODEL = "gpt-5.4-mini"

client = OpenAI(api_key=OPENAI_API_KEY)


def build_context(chunks: List[Dict]) -> str:
    """
    Build an evidence block from retrieved chunks.

    Args:
        chunks: Retrieved chunks

    Returns:
        A formatted string combining the retrieved evidence for prompting.
    """
    context_parts = []

    for i, chunk in enumerate(chunks, start=1):
        meta = chunk["metadata"]
        context_parts.append(
            f"""[Source {i}]
File: {meta.get('source_file', 'unknown')}
Product: {meta.get('product', 'N/A')}
Category: {meta.get('category', 'N/A')}
URL: {meta.get('url', 'N/A')}

{chunk["text"]}
"""
        )

    return "\n\n".join(context_parts)


def answer_query(query: str, top_k: int = 2) -> tuple[str, List[Dict]]:
    """
    Retrieve evidence and generate a grounded answer.
    Returns the answer text plus the retrieved chunks.

    Args:
        query: The user's input question.
        top_k: The number of top relevant chunks to retrieve for evidence.

    Returns:
        A tuple containing the generated answer text and the list of retrieved chunks
        for evidence.
    """
    chunks = retrieve_chunks(query, top_k=top_k)
    context = build_context(chunks)

    prompt = f"""
You are BoostRAG, a BMW M340i aftermarket parts research assistant.

Answer the user's question using only the retrieved evidence below.
Do not invent facts.
If the evidence is insufficient or conflicting, say so clearly.
When possible, mention the product or source supporting the answer.
Keep the answer concise and user-friendly.

User question:
{query}

Retrieved evidence:
{context}
"""

    response = client.responses.create(
        model=GEN_MODEL,
        input=prompt,
    )

    return response.output_text.strip(), chunks


def print_sources(chunks: List[Dict]) -> None:
    """
    Print a short de-duplicated source list.
    """
    seen = set()

    print("\nSources used:")
    for chunk in chunks:
        meta = chunk["metadata"]
        source_file = meta.get("source_file", "unknown")
        product = meta.get("product", "N/A")

        key = (source_file, product)
        if key in seen:
            continue

        print(f"- {source_file} | {product}")
        seen.add(key)


if __name__ == "__main__":
    user_query = input("Enter your question: ").strip()

    answer_text, chunks = answer_query(user_query, top_k=2)

    print("\nAnswer:\n")
    print(answer_text)

    print_sources(chunks)