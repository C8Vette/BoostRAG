from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from answer import answer_query
from chunk_embed import ensure_chroma_collection


app = FastAPI(title="BoostRAG API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    query: str
    top_k: int = 2


class Source(BaseModel):
    source_file: str | None = None
    product: str | None = None
    category: str | None = None
    brand: str | None = None
    url: str | None = None
    price: str | None = None
    distance: float | None = None
    text_preview: str | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]


@app.on_event("startup")
def startup_event() -> None:
    """
    Ensure the local Chroma collection exists before accepting questions.
    """
    ensure_chroma_collection()


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "BoostRAG API is running"}


@app.post("/ask", response_model=AskResponse)
def ask_boostrag(request: AskRequest) -> AskResponse:
    query = request.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        answer_text, chunks = answer_query(query=query, top_k=request.top_k)

        sources: list[Source] = []

        seen: set[tuple[str | None, str | None]] = set()

        for chunk in chunks:
            metadata: dict[str, Any] = chunk.get("metadata", {})
            source_file = metadata.get("source_file")
            product = metadata.get("product")

            key = (source_file, product)
            if key in seen:
                continue
            seen.add(key)

            sources.append(
                Source(
                    source_file=source_file,
                    product=product,
                    category=metadata.get("category"),
                    brand=metadata.get("brand"),
                    url=metadata.get("url"),
                    price=metadata.get("price"),
                    distance=chunk.get("distance"),
                    text_preview=chunk.get("text", "")[:350],
                )
            )

        return AskResponse(answer=answer_text, sources=sources)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"BoostRAG failed to answer the query: {exc}",
        ) from exc