import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("REDIS_URL", "")

import app as dvapp


def test_sse_stream_starts_with_retry_connected_event_and_safe_headers():
    dvapp.app.config["TESTING"] = True
    client = dvapp.app.test_client()

    resp = client.get("/api/events/stream", buffered=False)

    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("text/event-stream")
    assert resp.headers["Cache-Control"] == "no-cache"
    assert resp.headers["X-Accel-Buffering"] == "no"
    assert "Connection" not in resp.headers

    first_chunk = next(resp.response).decode("utf-8")
    assert "retry: " in first_chunk
    assert "event: connected" in first_chunk
    assert "data: {\"client_id\":\"" in first_chunk


def test_frontend_sse_rotates_quietly_without_default_console_noise():
    with open("static/index-v2-prototype.html", "r", encoding="utf-8") as fh:
        src = fh.read()

    assert "addEventListener('renew'" in src
    assert "window._dotverseSSE" in src
    assert "window.DOTVERSE_DEBUG_SSE" in src
    assert "console.warn('[SSE] Connection error, reconnecting...')" not in src
