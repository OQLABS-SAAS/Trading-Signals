# DotVerse — Session Handoff 2026-05-08

## CRITICAL: Read this entire document before touching any code.

---

## Current State

Site is deployed and running at `https://dot-verse.up.railway.app/`. Single Railway service (web only, worker service was deleted). Python 3.12.13. TradingAgents installed and running. OpenRouter API key configured.

API status: `GET /api/verdict/status` returns all green.

---

## What's Working

### Pipeline (6 steps)
- Market → Signal → Understand → Verdict → Size → Act
- All footer step numbers updated to "X of 6"
- Sidebar nav items + pipeline breadcrumb pills all correct
- Verdict sits between Understand and Size

### Verdict Tab
- `showVerdict()` renders "Run Analysis" button when signal is loaded
- `_vRunAnalysis()` triggers live TradingAgents analysis via OpenRouter
- `_vFetchLive()` calls `/api/verdict` POST → `_vPollResult()` polls `/api/verdict/result/<job_id>` 
- Banner shows exact status: red=error, amber=running, green=complete
- No mock/fake data — only real TradingAgents output when available
- `_vPreloadSize()` carries verdict plan to Size tab via `window._verdictPlan`
- CTA: Understand → "→ Verdict" (primary), Size tab → "Verdict" button

### Backend
- `/api/verdict` POST — requires auth, enqueues RQ job
- `/api/verdict/result/<job_id>` GET — polls job status
- `/api/verdict/status` GET — public diagnostic (no auth)
- `_run_verdict_job(ticker, trade_date)` — RQ worker function
- TradingAgents config: DeepSeek V4, 0 debate rounds, 0 risk rounds

### Size Tab
- `window._verdictPlan` data flow from Verdict
- Verdict plan banner shows 5-trade ladder with risk %, stops, trailing
- Clear button resets `_verdictPlan`

---

## What's BROKEN

### 1. RQ Worker — NOT processing jobs
**Symptom:** Verdict "Run Analysis" enqueues job but never completes. Backtest also returns empty.
**Root cause:** The Procfile had `worker: rq worker` but the worker service created from it had NO environment variables (REDIS_URL was empty → tried localhost:6379 → crashed). Worker service was deleted. Last attempt: adding RQ worker as a daemon thread inside gunicorn — this CRASHED the site (commit `8136c67` reverted as `4671fa9`).

**Current Procfile:**
```
web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120
```

**WHAT NEEDS TO BE FIXED:** The RQ worker needs to process jobs. Options:
A. Recreate worker service WITH env vars (REDIS_URL, DATABASE_URL, SECRET_KEY, OPENROUTER_API_KEY all copied from web service)
B. Start RQ worker thread inside gunicorn but TEST LOCALLY FIRST before pushing

### 2. Tab change kills polling interval
**Symptom:** If user switches tabs during Verdict analysis, the results are lost.
**Partial fix applied:** Interval stored on `window._verdictPollInterval` and cleared on Verdict page load. But `_vRenderLive` still tries to find DOM elements that may have been removed.

### 3. Stuck old RQ jobs in Redis queue
Old slow jobs from previous config (with 15 LLM calls) are still in Redis. They process first (FIFO) before new jobs. Need to clear or wait for them.

---

## What Was Attempted and Failed

### Failed: Force push (`a3af662` → `8136c67`)
`git add .` accidentally staged hundreds of files. Force push crashed Railway. Reverted.

### Failed: RQ worker as gunicorn thread (`8136c67`, reverted)
Added daemon thread at module level. Caused 502 on Railway. Root cause unknown — didn't test locally.

### Failed: Separate worker service (multiple attempts)
Worker created from Procfile but had no env vars. User had to manually delete it.

---

## Key Files Changed

| File | Lines | What |
|------|-------|------|
| `static/index-v2-prototype.html` | +250 | Verdict tab, CTA buttons, pipeline reorder, _verdictPlan |
| `app.py` | +100 | Verdict endpoints, TradingAgents config, diagnostic endpoint |
| `requirements.txt` | +2 | tradingagents, langgraph |
| `runtime.txt` | 1 new file | python-3.12 |
| `Procfile` | 1 line removed | worker service deleted |

---

## Git History (this session)

```
4671fa9 Revert crashing worker thread commit
8136c67 (reverted) Worker thread + clear queue
5d20a0d RQ worker as gunicorn thread + debate rounds 0
f0c31a0 REDIS_URL fix for worker
84f7592 _vRunAnalysis fix + _vRenderLive fix
61411d9 Remove auto-start of analysis
4a03540 Remove mock data + diagnostic endpoint
a209d17 Revert unauthorized push
1ad67f7 (reverted) Remove mock data
f8f0db5 Diagnostic banner
8cee6f7 Pipeline order 1-6
5ba1317 Verdict CTA buttons
00131df Backend TradingAgents + RQ worker
d761605 Risk tolerance mapping 5/10/20
d4888f8 Settings wiring
a09c4be Signal tab fixes
1c36cc2 Market tab fixes
```

---

## Environment (Railway)

| Variable | Service |
|----------|---------|
| SECRET_KEY | web |
| DATABASE_URL | web |
| REDIS_URL | web |
| OPENROUTER_API_KEY | web |
| FINNHUB_API_KEY | web |
| TWELVEDATA_API_KEY | web |

Worker service (if recreated) needs ALL of these.

---

## DO NOT:
- Use `git add .` — only stage individual files
- Force push without explicit user approval
- Add mock/fake data — the user rejected it
- Make a separate worker service without ensuring env vars are copied
- Push without verifying in a live browser first
- Suggest untested model changes (Gemini Flash, etc.)
