import os
import sys


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as dvapp


class _FakeJob:
    def __init__(self, job_id, finished=False, failed=False):
        self.id = job_id
        self.is_finished = finished
        self.is_failed = failed


class _FakeQueue:
    def __init__(self):
        self.jobs = {}
        self.count = 0

    def enqueue(self, *args, **kwargs):
        job = _FakeJob(f"job-{len(self.jobs) + 1}")
        self.jobs[job.id] = job
        self.count += 1
        return job

    def fetch_job(self, job_id):
        return self.jobs.get(job_id)


def _authed_client():
    dvapp.app.config["TESTING"] = True
    dvapp.app.config["SECRET_KEY"] = "test-secret-key-not-for-prod"
    client = dvapp.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = "testuser"
        sess["logged_in"] = True
        sess["user_tier"] = "pro"
    return client


def test_paid_diagnostics_are_not_public_and_do_not_expose_key_prefix():
    source = (os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(os.path.join(source, "app.py"), encoding="utf-8") as fh:
        app_source = fh.read()

    diag_start = app_source.index("def diag_eodhd():")
    diag_end = app_source.index("@app.route(\"/api/diag-scan\"", diag_start)
    diag_source = app_source[diag_start:diag_end]
    assert "key_prefix" not in diag_source
    assert "@app.route(\"/api/diag-eodhd\", methods=[\"GET\"])\n@login_required\n@require_admin" in app_source
    assert "@app.route(\"/api/diag-scan\", methods=[\"GET\"])\n@login_required\n@require_admin" in app_source

    client = dvapp.app.test_client()
    assert client.get("/api/diag-eodhd").status_code == 401
    assert client.get("/api/diag-scan").status_code == 401


def test_verdict_enqueue_dedupes_inflight_ticker_timeframe(monkeypatch):
    fake_queue = _FakeQueue()
    monkeypatch.setattr(dvapp, "_rq_queue", fake_queue)
    monkeypatch.setattr(dvapp, "_redis_client", None)
    monkeypatch.setattr(dvapp, "TA_AVAILABLE", True)
    dvapp._verdict_rate_store.clear()
    dvapp._verdict_inflight_store.clear()

    client = _authed_client()
    first = client.post("/api/verdict", json={"ticker": "eurusd", "timeframe": "1h"})
    second = client.post("/api/verdict", json={"ticker": "EURUSD", "timeframe": "1h"})

    assert first.status_code == 200, first.get_data(as_text=True)
    assert first.get_json()["job_id"] == "job-1"
    assert first.get_json()["deduped"] is False
    assert second.status_code == 200, second.get_data(as_text=True)
    assert second.get_json()["job_id"] == "job-1"
    assert second.get_json()["deduped"] is True
    assert fake_queue.count == 1


def test_verdict_enqueue_rate_limits_expensive_requests(monkeypatch):
    fake_queue = _FakeQueue()
    monkeypatch.setattr(dvapp, "_rq_queue", fake_queue)
    monkeypatch.setattr(dvapp, "_redis_client", None)
    monkeypatch.setattr(dvapp, "TA_AVAILABLE", True)
    dvapp._verdict_rate_store.clear()
    dvapp._verdict_inflight_store.clear()

    client = _authed_client()
    for ticker in ("AAPL", "MSFT", "NVDA"):
        resp = client.post("/api/verdict", json={"ticker": ticker, "timeframe": "1h"})
        assert resp.status_code == 200, resp.get_data(as_text=True)

    limited = client.post("/api/verdict", json={"ticker": "TSLA", "timeframe": "1h"})
    assert limited.status_code == 429, limited.get_data(as_text=True)
    data = limited.get_json()
    assert data["error"] == "verdict_rate_limit"
    assert data["limit"] == dvapp.VERDICT_RATE_LIMIT
