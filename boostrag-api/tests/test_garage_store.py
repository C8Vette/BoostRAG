import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_build_context_block():
    import garage_store
    data = {"garage": {"year": 2021, "model": "M340i", "trim": "xDrive"},
            "mods": [{"category": "Intake & Exhaust", "name": "VRSF downpipe"},
                     {"category": "Engine", "name": "BM3 tune"}]}
    block = garage_store.build_context_block(data)
    assert "2021" in block and "M340i" in block and "xDrive" in block
    assert "VRSF downpipe" in block and "BM3 tune" in block


def test_build_context_block_empty():
    import garage_store
    assert garage_store.build_context_block({"garage": None, "mods": []}) == ""


def test_get_garage_filters_by_uid(monkeypatch):
    import garage_store
    calls = []

    def fake_req(method, path, **kw):
        calls.append((method, path))
        if path.startswith("/garages"):
            return [{"id": "g1", "user_id": "u1", "year": 2021, "model": "M340i", "trim": "xDrive", "context_on": True}]
        return [{"id": "m1", "garage_id": "g1", "category": "Engine", "name": "BM3"}]

    monkeypatch.setattr(garage_store, "_req", fake_req)
    out = garage_store.get_garage("u1")
    assert out["garage"]["model"] == "M340i"
    assert out["mods"][0]["name"] == "BM3"
    assert any("user_id=eq.u1" in p for _, p in calls)   # scoped by uid


def test_add_mod_rejects_when_no_garage(monkeypatch):
    import garage_store
    monkeypatch.setattr(garage_store, "_req", lambda m, p, **k: [])  # no garage
    with pytest.raises(garage_store.GarageUnavailable):
        garage_store.add_mod("u1", "Engine", "BM3", None)


def test_add_mod_stamps_garage_from_uid(monkeypatch):
    import garage_store
    seen = {}

    def fake_req(method, path, **kw):
        if method == "GET":
            return [{"id": "g-real"}]
        seen["body"] = kw.get("json")
        return [kw.get("json")]

    monkeypatch.setattr(garage_store, "_req", fake_req)
    garage_store.add_mod("u1", "Engine", "BM3", None)
    assert seen["body"]["garage_id"] == "g-real"   # server-derived, not body-supplied


def test_unavailable_when_env_absent(monkeypatch):
    import garage_store
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(garage_store.GarageUnavailable):
        garage_store._req("GET", "/garages")
