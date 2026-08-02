import sys, time
from pathlib import Path
import jwt
import pytest
from fastapi import HTTPException
sys.path.insert(0, str(Path(__file__).parent.parent))

SECRET = "test-secret"


def _tok(sub="user-123", exp_delta=3600, aud="authenticated", secret=SECRET):
    payload = {"sub": sub, "aud": aud, "exp": int(time.time()) + exp_delta}
    return jwt.encode(payload, secret, algorithm="HS256")


class _Req:
    def __init__(self, auth=None):
        self.headers = {"Authorization": auth} if auth else {}


def test_verify_valid_token(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    import auth
    assert auth.verify_token(_tok()) == "user-123"


def test_verify_rejects_expired_and_bad_sig(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    import auth
    assert auth.verify_token(_tok(exp_delta=-10)) is None
    assert auth.verify_token(_tok(secret="wrong")) is None
    assert auth.verify_token("not.a.jwt") is None


def test_verify_none_when_secret_absent(monkeypatch):
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    import auth
    assert auth.verify_token(_tok()) is None   # anonymous-only locally


def test_optional_user_never_raises(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    import auth
    assert auth.optional_user(_Req()) is None
    assert auth.optional_user(_Req(f"Bearer {_tok()}")) == "user-123"
    assert auth.optional_user(_Req("Bearer garbage")) is None


def test_require_user_raises_401(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    import auth
    with pytest.raises(HTTPException) as e:
        auth.require_user(_Req())
    assert e.value.status_code == 401
    assert auth.require_user(_Req(f"Bearer {_tok()}")) == "user-123"
