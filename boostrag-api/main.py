from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from orchestrator import answer_question
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
    origin: str | None = None
    trust_tier: str | None = None
    text_preview: str | None = None


class AskResponse(BaseModel):
    answer: str
    origin: str
    confidence: dict = {}
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
        result = answer_question(query=query, top_k=request.top_k)
        sources = [Source(**{k: v for k, v in s.items() if k in Source.model_fields}) for s in result.sources]
        return AskResponse(
            answer=result.answer,
            origin=result.origin,
            confidence=result.confidence,
            sources=sources,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"BoostRAG failed to answer the query: {exc}",
        ) from exc