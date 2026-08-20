from __future__ import annotations

import logging
import os
from functools import lru_cache

import jwt
from fastapi import HTTPException, Request

_AUD = "authenticated"
_log = logging.getLogger("uvicorn.error")  # configured handler → messages surface


@lru_cache(maxsize=4)
def _jwk_client(jwks_url: str) -> jwt.PyJWKClient:
    """Cached JWKS client per URL; it also caches the fetched public keys."""
    return jwt.PyJWKClient(jwks_url, cache_keys=True)


def _decode_asymmetric(token: str) -> dict | None:
    """Verify a token signed with the project's asymmetric key (ES256/RS256).

    Supabase's current default. The public key comes from the project's JWKS
    endpoint (derived from SUPABASE_URL) — no secret required.
    """
    url = os.getenv("SUPABASE_URL")
    if not url:
        return None
    jwks_url = f"{url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    try:
        signing_key = _jwk_client(jwks_url).get_signing_key_from_jwt(token)
        return jwt.decode(
            token, signing_key.key, algorithms=["ES256", "RS256"], audience=_AUD
        )
    except Exception as exc:  # noqa: BLE001 -- never raise; log why for diagnosis
        # Network error, no matching key, bad signature, expired — all → anonymous.
        _log.warning("asymmetric verify failed: %s: %s", type(exc).__name__, exc)
        return None


def _decode_hs256(token: str) -> dict | None:
    """Verify a token signed with the legacy HS256 shared secret."""
    secret = os.getenv("SUPABASE_JWT_SECRET")
    if not secret:
        return None
    try:
        return jwt.decode(token, secret, algorithms=["HS256"], audience=_AUD)
    except jwt.PyJWTError:
        return None


def verify_token(token: str) -> str | None:
    """Return the Supabase user id (sub) for a valid JWT, else None. Never raises.

    Supports both Supabase signing schemes and routes by the token's header:
    legacy HS256 shared secret, or the current asymmetric keys (ES256/RS256)
    verified against the project's public JWKS.
    """
    if not token:
        return None  # anonymous request — normal, no log
    try:
        alg = jwt.get_unverified_header(token).get("alg", "")
    except jwt.PyJWTError as exc:
        _log.warning("verify_token: malformed token header: %s", exc)
        return None
    claims = _decode_hs256(token) if alg == "HS256" else _decode_asymmetric(token)
    if not claims:
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
