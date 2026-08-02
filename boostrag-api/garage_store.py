from __future__ import annotations

import os
import httpx


class GarageUnavailable(Exception):
    """Supabase is unconfigured or unreachable — callers should degrade gracefully."""


def _req(method: str, path: str, *, json=None, prefer: str = "return=representation"):
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise GarageUnavailable("Supabase not configured")
    headers = {"apikey": key, "Authorization": f"Bearer {key}",
               "Content-Type": "application/json", "Prefer": prefer}
    try:
        resp = httpx.request(method, f"{url}/rest/v1{path}", headers=headers, json=json, timeout=8)
        resp.raise_for_status()
        return resp.json() if resp.content else []
    except (httpx.HTTPError, ValueError) as exc:
        raise GarageUnavailable(str(exc)) from exc


def get_garage(uid: str) -> dict | None:
    rows = _req("GET", f"/garages?user_id=eq.{uid}&select=*")
    if not rows:
        return {"garage": None, "mods": []}
    garage = rows[0]
    mods = _req("GET", f"/garage_mods?garage_id=eq.{garage['id']}&select=*&order=created_at")
    return {"garage": garage, "mods": mods}


def upsert_garage(uid: str, year: int, model: str, trim: str | None, context_on: bool) -> dict:
    body = {"user_id": uid, "year": year, "model": model, "trim": trim, "context_on": context_on}
    rows = _req("POST", "/garages?on_conflict=user_id", json=body,
                prefer="resolution=merge-duplicates,return=representation")
    return rows[0] if rows else body


def _garage_id_for(uid: str) -> str:
    rows = _req("GET", f"/garages?user_id=eq.{uid}&select=id")
    if not rows:
        raise GarageUnavailable("No garage for user")
    return rows[0]["id"]


def add_mod(uid: str, category: str, name: str, source_url: str | None) -> dict:
    gid = _garage_id_for(uid)
    body = {"garage_id": gid, "category": category, "name": name, "source_url": source_url}
    rows = _req("POST", "/garage_mods", json=body)
    return rows[0] if rows else body


def delete_mod(uid: str, mod_id: str) -> None:
    gid = _garage_id_for(uid)
    _req("DELETE", f"/garage_mods?id=eq.{mod_id}&garage_id=eq.{gid}")


def build_context_block(data: dict) -> str:
    garage = (data or {}).get("garage")
    if not garage:
        return ""
    trim = f" {garage['trim']}" if garage.get("trim") else ""
    line = f"The user drives a {garage.get('year')} BMW {garage.get('model')}{trim}."
    mods = (data or {}).get("mods") or []
    if mods:
        listed = ", ".join(f"{m['name']} ({m['category']})" for m in mods)
        line += f" Installed modifications: {listed}."
    return line
