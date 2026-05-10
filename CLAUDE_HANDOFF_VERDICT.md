# Verdict Tab — Handover for Sonnet · 2026-05-08

## Scope (USER-LOCKED)
**Only the Verdict button issue.** All other tasks — full 1-30 audit, BUG 1/2 reverify, visual previews, mock site — explicitly dropped per the user. Don't touch anything outside the Verdict feature.

---

## What's working (don't re-do)

- Two fixes shipped and live on Railway:
  - `af781f0` — RQ worker now runs as its own process under `start.sh`. The previous in-process daemon thread that crashed Railway (commit 8136c67) is gone. `Procfile` invokes `bash start.sh`, which spawns `python run_worker.py &` then `exec gunicorn`. `run_worker.py` rewritten for rq 2.x compatibility (dropped the removed `Connection` import). Plus `/api/verdict/status` extended with worker/queue diagnostics, plus admin `POST /api/verdict/queue/clear` to drain stuck FIFO jobs.
  - `e766371` — VERDICT step added to breadcrumbs on Signal / Understand / Act views (3 lines). All 6 pipeline views now show `MARKET › SIGNAL › UNDERSTAND › VERDICT › SIZE › ACT` consistently with the active step in `<em>`.

- Live diagnostic confirms backend health:
  ```
  curl https://dot-verse.up.railway.app/api/verdict/status
  → {"rq_workers_alive":1, "rq_queue_depth":0, "rq_queue_failed":0,
     "ta_available":true, "openrouter_key_configured":true, ...}
  ```

- Breadcrumb fix verified visually — screenshot shows VERDICT highlighted in amber on the Verdict view, no double-chevron gap.

---

## What's stuck (the actual handover)

**Symptom:** clicking "Run Analysis" on the Verdict page gets stuck in "Analysing… 8 agents studying the market" indefinitely. After 5+ minutes the result never appears in the UI.

**Reproduction (verified by me):**
1. Land on dashboard signed in as Omar (admin / Beginner).
2. Click `Analyse →` on the BTCUSD card in Top 10 Winning Opportunities. Understand tab loads with full BTC analysis.
3. Click `Verdict` in left sidebar. Verdict page loads correctly: breadcrumb has VERDICT highlighted, BUY hero shows entry/SL/TP, green "Ready" banner, "Run Deep Analysis" CTA visible.
4. Click `Run Analysis`. Banner switches to amber "Analysing… 8 agents studying the market". This part works.
5. Wait. After 60-90s — when the handoff says results normally arrive — nothing changes. After 5 minutes — still nothing.

**Backend evidence the worker is fine:**
- `/api/verdict/status` consistently shows `rq_workers_alive=1`, `queue_depth=0`, `queue_failed=0` throughout the wait. The job got picked up off the queue. It either completed silently or is still running on the worker. The current public diagnostic doesn't distinguish those two.

**Frontend evidence the polling broke:**
Captured from the browser console while the banner was stuck:
```
_verdictRunning      = true
_verdictPollInterval = 48          ← number, so setInterval is "scheduled"
_verdictPlan         = null
_activeSignal.sym    = "BTCUSD"
```

I monkey-patched `window.fetch` and `XMLHttpRequest.prototype.open` to capture every call to `/api/verdict/*`. Across 28+ seconds of observation: **ZERO calls captured.** The poll interval ID is a live number, but the callback isn't actually hitting the network.

**Possible root causes (ranked by likelihood):**

1. **The polling callback is hitting an early return** — e.g. the function checks for some `_verdictJobId` that wasn't set, or for a DOM element that no longer exists, then silently returns without scheduling a fetch. The interval keeps firing but does nothing.
2. **`clearInterval` was called but the variable wasn't nulled** — so `_verdictPollInterval` is a stale number and `setInterval(callback, n)` is no longer firing. (Possible per the prior handoff note: *"Interval stored on `window._verdictPollInterval` and cleared on Verdict page load. But `_vRenderLive` still tries to find DOM elements that may have been removed."*)
3. **The `_vRunAnalysis` POST never returned a job_id** — so the polling function has nothing to fetch. The amber banner switched on optimistically before the POST resolved.

**What I couldn't do from this session:**
- Read the source of `_vRunAnalysis` / `_vPollResult` / `_vRenderLive` via the JS console — the Chrome MCP filter blocks function-source dumps. Source is in `static/index-v2-prototype.html` and readable directly via the Read tool.

---

## Where to start

### Step 1 — read the actual functions
Grep `static/index-v2-prototype.html` for `_vRunAnalysis`, `_vPollResult`, `_vRenderLive`, `_vFetchLive`, `_vShowBanner`, `_verdictJobId`, `_verdictPollInterval`. Trace the full flow from button click → POST `/api/verdict` → store job_id → start setInterval → poll `/api/verdict/result/<job_id>` → on done call `_vRenderLive` to display. Look for:
- Where `job_id` from the POST response is stored. Is it on `window._verdictJobId` or somewhere else?
- The early-return conditions in the poll callback. If `_verdictJobId` is missing or a DOM element isn't found, does it bail without doing anything?
- Whether `clearInterval` is followed by `window._verdictPollInterval = null`.

### Step 2 — extend the diagnostic
Add to `/api/verdict/status` (in `app.py` around line 8372): `rq_jobs_started` count via `StartedJobRegistry` and `rq_jobs_finished` count via `FinishedJobRegistry`. That tells us at a glance whether the worker is still chewing on the job or finished and the result is sitting in Redis waiting to be fetched.

### Step 3 — reproduce in browser with DevTools
On `https://dot-verse.up.railway.app` → DevTools → Network. Click Run Analysis. Watch:
- Is `POST /api/verdict` 200 with `{job_id: "..."}`?
- Are subsequent `GET /api/verdict/result/<job_id>` calls firing every N seconds?
- If they ARE firing, what does the JSON say? `{status: "started"}` means worker still working. `{status: "finished", result: ...}` means worker done — and that's where `_vRenderLive` should fire.

### Step 4 — fix
Once root cause is pinned, the fix is almost certainly a small JS change (5-20 lines) in `static/index-v2-prototype.html` — either properly storing the job_id, properly nulling the interval handle, or fixing the polling callback's early-return logic. It is NOT a backend change; backend is healthy.

---

## Constraints (from CLAUDE_HANDOFF.md, still active)

**DO NOT:**
- Use `git add .` — only stage individual files. The repo has dozens of untracked preview/audit files that must NOT enter commits.
- Force push without explicit user approval.
- Add mock/fake data to bypass the issue. The user explicitly rejected this.
- Push without verifying in a live browser first.
- Suggest untested model changes (Gemini Flash, etc.).

**DO:**
- Sandbox-test backend changes against the real `app.py` before pushing. The user's sandbox has redislite + rq + flask installed; you can spin up a Redis on a test port and run `python run_worker.py` against it to verify imports + dispatch work.
- Two-gate every commit + push. The user pushes manually from their terminal because the sandbox doesn't have GitHub auth.
- After deploying, hit `/api/verdict/status` to confirm worker is still alive (the start.sh process model means a deploy-time error would show `workers_alive=0`).

---

## Files touched this session (already on main, both pushed)

| File | Change |
|---|---|
| `Procfile` | `web: bash start.sh` |
| `start.sh` | new, executable |
| `run_worker.py` | rewritten for rq 2.x |
| `app.py` | removed in-process daemon thread; extended `/api/verdict/status`; added `/api/verdict/queue/clear` |
| `static/index-v2-prototype.html` | breadcrumbs on Signal/Understand/Act now include VERDICT |

---

## Quick environmental facts

- Site: `https://dot-verse.up.railway.app`
- User account: Omar / admin / Beginner mode
- Python on Railway: 3.12.13
- rq version (current): 2.x (sandbox confirmed 2.8.0)
- Redis: cross-project Railway add-on, accessed via `REDIS_URL` env var
- TradingAgents config: `deepseek/deepseek-v4-pro` via OpenRouter, `max_debate_rounds=0`, `max_risk_discuss_rounds=0`
- Memory MCP entity: `DotVerse Verdict Session 2026-05-08 part 2` — full session state stored there

Good luck.
