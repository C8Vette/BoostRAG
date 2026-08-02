from __future__ import annotations

import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from orchestrator import answer_question
from chunk_embed import ensure_chroma_collection
from provenance import asks_today, increment_ask
from browse import browse_category
from auth import optional_user, require_user
import garage_store


app = FastAPI(title="BoostRAG API")

BUSY_MESSAGE = "BoostRAG has had a busy day and hit its demo limit. Please check back tomorrow!"

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "You're asking a lot, very fast — please slow down and try again in a minute."},
    )


_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
_allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    query: str
    top_k: int = 2
    use_context: bool = True


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
@limiter.limit(lambda: os.getenv("RATE_LIMIT", "20/minute"))
def ask_boostrag(request: Request, payload: AskRequest) -> AskResponse:
    query = payload.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    cap = int(os.getenv("DAILY_ASK_CAP", "500"))
    if asks_today() >= cap:
        return AskResponse(answer=BUSY_MESSAGE, origin="none", confidence={}, sources=[])
    increment_ask()

    user_context = None
    if payload.use_context:
        uid = optional_user(request)
        if uid:
            try:
                data = garage_store.get_garage(uid)
                if data and data.get("garage") and data["garage"].get("context_on", True):
                    user_context = garage_store.build_context_block(data) or None
            except garage_store.GarageUnavailable:
                user_context = None      # degrade gracefully — answer without personalization

    try:
        result = answer_question(query=query, top_k=payload.top_k, user_context=user_context)
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


@app.get("/browse")
@limiter.limit(lambda: os.getenv("RATE_LIMIT", "20/minute"))
def browse(request: Request, category: str) -> dict:
    result = browse_category(category)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Unknown category: {category}")
    return result


class GarageIn(BaseModel):
    year: int
    model: str
    trim: str | None = None
    context_on: bool = True


class ModIn(BaseModel):
    category: str
    name: str
    source_url: str | None = None


@app.get("/garage")
@limiter.limit(lambda: os.getenv("RATE_LIMIT", "20/minute"))
def get_garage(request: Request):
    uid = require_user(request)
    try:
        return garage_store.get_garage(uid)
    except garage_store.GarageUnavailable:
        raise HTTPException(status_code=503, detail="Garage is temporarily unavailable.")


@app.put("/garage")
@limiter.limit(lambda: os.getenv("RATE_LIMIT", "20/minute"))
def put_garage(request: Request, payload: GarageIn):
    uid = require_user(request)
    try:
        return garage_store.upsert_garage(uid, payload.year, payload.model, payload.trim, payload.context_on)
    except garage_store.GarageUnavailable:
        raise HTTPException(status_code=503, detail="Garage is temporarily unavailable.")


@app.post("/garage/mods")
@limiter.limit(lambda: os.getenv("RATE_LIMIT", "20/minute"))
def post_mod(request: Request, payload: ModIn):
    uid = require_user(request)
    try:
        return garage_store.add_mod(uid, payload.category, payload.name, payload.source_url)
    except garage_store.GarageUnavailable:
        raise HTTPException(status_code=503, detail="Garage is temporarily unavailable.")


@app.delete("/garage/mods/{mod_id}")
@limiter.limit(lambda: os.getenv("RATE_LIMIT", "20/minute"))
def delete_mod(request: Request, mod_id: str):
    uid = require_user(request)
    try:
        garage_store.delete_mod(uid, mod_id)
        return {"deleted": mod_id}
    except garage_store.GarageUnavailable:
        raise HTTPException(status_code=503, detail="Garage is temporarily unavailable.")