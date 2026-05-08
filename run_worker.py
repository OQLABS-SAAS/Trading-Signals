"""RQ Worker launcher — runs as its own process under start.sh.

Invoked by Procfile via start.sh — gunicorn runs in the foreground, this worker
runs alongside it as a background subprocess. Both inherit the web service's
env vars (REDIS_URL, DATABASE_URL, OPENROUTER_API_KEY, ...).

Compatible with rq 1.x and rq 2.x — Connection() was removed in 2.x, so we pass
the connection straight to Queue/Worker and skip the context manager.
"""
import os
import sys

os.environ.setdefault("WORKER_MODE", "1")

from redis import Redis
from rq import Worker, Queue

# Importing app gives the worker every job function (_run_verdict_job,
# _run_backtest_job, etc.) along with DB / TradingAgents imports.
import app  # noqa: F401

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
print(f"[worker] connecting to redis at {redis_url[:30]}...", flush=True)

conn  = Redis.from_url(redis_url)
queue = Queue("default", connection=conn)
print(f"[worker] queue 'default' depth at start: {queue.count}", flush=True)
print("[worker] starting worker — listening for jobs", flush=True)

# `with_scheduler=True` lets us schedule deferred jobs in the future without
# adding a separate rqscheduler process. Safe even if no scheduled jobs exist.
Worker([queue], connection=conn).work(with_scheduler=True)
