"""S-4: CORS must not be wildcard-with-credentials. An arbitrary website must not
be able to make authenticated cross-origin requests on a logged-in user's behalf."""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("REDIS_URL", "")

import app as dvapp


def _client():
    dvapp.app.config["TESTING"] = True
    return dvapp.app.test_client()


def test_cors_does_not_reflect_unknown_origin():
    r = _client().get("/health", headers={"Origin": "https://evil.example.com"})
    acao = r.headers.get("Access-Control-Allow-Origin")
    assert acao != "https://evil.example.com", "arbitrary origins must not be allowed"


def test_cors_allows_prod_origin():
    r = _client().get("/health", headers={"Origin": "https://dot-verse.up.railway.app"})
    assert r.headers.get("Access-Control-Allow-Origin") == "https://dot-verse.up.railway.app"


def test_cors_allows_localhost_dev():
    r = _client().get("/health", headers={"Origin": "http://localhost:3000"})
    assert r.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
