#!/usr/bin/env bash
# DotVerse boot — starts the RQ worker as a background process and gunicorn as
# the foreground (PID 1) process. Both inherit the web service's env vars
# (REDIS_URL, DATABASE_URL, OPENROUTER_API_KEY, etc.) automatically.
#
# Why a separate process for the worker (not a thread inside gunicorn):
#   - RQ's Worker.work() forks child processes for each job; fork() inside a
#     daemon thread under the GIL is fragile and was the cause of the previous
#     Railway crash (commit 8136c67, reverted as 4671fa9).
#   - A long-running TradingAgents analysis can exceed gunicorn's 120s timeout,
#     which would kill the in-process worker mid-job.
#   - Running the worker as its own process gives it independent lifecycle,
#     clean fork() semantics, and proper isolation from the web request path.

set -e

PORT="${PORT:-5000}"
WORKERS="${WEB_CONCURRENCY:-1}"
TIMEOUT="${WEB_TIMEOUT:-120}"

echo "[boot] DotVerse starting"
echo "[boot] PORT=$PORT WORKERS=$WORKERS TIMEOUT=$TIMEOUT"
echo "[boot] REDIS_URL configured: $([ -n "$REDIS_URL" ] && echo yes || echo no)"
echo "[boot] DATABASE_URL configured: $([ -n "$DATABASE_URL" ] && echo yes || echo no)"
echo "[boot] OPENROUTER_API_KEY configured: $([ -n "$OPENROUTER_API_KEY" ] && echo yes || echo no)"

# Start RQ worker in the background so jobs (verdict / backtest) actually run.
echo "[boot] Launching RQ worker process"
python run_worker.py &
WORKER_PID=$!

# If gunicorn dies or receives SIGTERM, take the worker down with it.
trap 'echo "[boot] Shutdown requested — stopping worker (PID $WORKER_PID)"; kill "$WORKER_PID" 2>/dev/null || true; exit 0' SIGTERM SIGINT

echo "[boot] Worker PID $WORKER_PID — starting gunicorn"

# exec replaces this shell with gunicorn so signals route correctly.
exec gunicorn app:app \
  --bind "0.0.0.0:$PORT" \
  --workers "$WORKERS" \
  --timeout "$TIMEOUT" \
  --access-logfile - \
  --error-logfile -
