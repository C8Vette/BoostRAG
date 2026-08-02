from __future__ import annotations

import os

import jwt
from fastapi import HTTPException, Request


def verify_token(token: str) -> str | None:
    """Return the Supabase user id (sub) for a valid JWT, else None. Never raises."""
    secret = os.getenv("SUPABASE_JWT_SECRET")
    if not secret or not token:
        return None
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
    except jwt.PyJWTError:
        return None
    sub = claims.get("sub")
    return sub or None


def _bearer(request: Request) -> str | None:
    header = request.headers.get("Authorization") or ""
    if header.startswith("Bearer "):
        return header[7:].strip()
    return None


def optional_user(request: Request) -> str | None:
    """User id if a valid token is present, else None. Never raises (anonymous ok)."""
    return verify_token(_bearer(request) or "")


def require_user(request: Request) -> str:
    """User id, or 401 if not authenticated."""
    uid = optional_user(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return uid
