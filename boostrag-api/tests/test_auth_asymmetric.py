import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

sys.path.insert(0, str(Path(__file__).parent.parent))


def _keypair():
    priv = ec.generate_private_key(ec.SECP256R1())
    return priv, priv.public_key()


def _es256(priv, sub="u-es", exp_delta=3600, aud="authenticated"):
    return jwt.encode(
        {"sub": sub, "aud": aud, "exp": int(time.time()) + exp_delta},
        priv,
        algorithm="ES256",
    )


def _client_returning(pub):
    return SimpleNamespace(get_signing_key_from_jwt=lambda _t: SimpleNamespace(key=pub))


def test_asymmetric_valid(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    import auth
    priv, pub = _keypair()
    token = _es256(priv)
    with patch.object(auth, "_jwk_client", return_value=_client_returning(pub)):
        assert auth.verify_token(token) == "u-es"   # ES256 verified via JWKS


def test_asymmetric_expired(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    import auth
    priv, pub = _keypair()
    token = _es256(priv, exp_delta=-10)
    with patch.object(auth, "_jwk_client", return_value=_client_returning(pub)):
        assert auth.verify_token(token) is None


def test_asymmetric_wrong_key(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    import auth
    priv, _ = _keypair()
    _, other_pub = _keypair()
    token = _es256(priv)
    with patch.object(auth, "_jwk_client", return_value=_client_returning(other_pub)):
        assert auth.verify_token(token) is None   # signature mismatch → anonymous


def test_asymmetric_no_url(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    import auth
    priv, _ = _keypair()
    assert auth.verify_token(_es256(priv)) is None   # can't build JWKS URL
