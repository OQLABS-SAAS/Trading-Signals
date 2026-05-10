# Verdict Feature — Integration Plan
## Mode: MAX (architectural — new endpoint, RQ worker, LLM integration)

---

## Setup
- **Provider:** OpenRouter
- **Deep model:** `deepseek/deepseek-v4-pro` (paid, ~15 calls)
- **Quick model:** `meta-llama/llama-3.3-70b-instruct:free` (free, ~3 calls)
- **Cost:** ~$0.01 per analysis
- **Speed:** 35–45 seconds per ticker

---

## Architecture

```
User clicks "Deep Analysis" on Understand page
        │
        ▼
POST /api/verdict {ticker: "BTCUSD", timeframe: "4H", entry: 82312, sl: 79009, tp: 90406}
        │
        ▼
app.py → enqueue RQ job "verdict_analysis"
        │
        ▼
RQ Worker picks up job
        │
        ▼
TradingAgentsGraph.propagate(ticker, date)
        │
        ├── Market Analyst (LLM) → OHLCV + indicators report
        ├── News Analyst (LLM) → news headlines report
        ├── Fundamentals Analyst (LLM) → balance sheet report
        ├── Social/Sentiment Analyst (LLM) → social mood report
        │
        ├── Bull Researcher vs Bear Researcher debate (LLM, 2+ rounds)
        ├── Judge (LLM) → picks winning argument
        │
        ├── Trader Agent (LLM) → writes trading plan
        │
        ├── Conservative vs Aggressive vs Neutral Risk debate (LLM)
        │
        └── Portfolio Manager (LLM) → final YES/NO + confidence
                │
                ▼
        Result saved to Redis: verdict:{ticker}:{tf} (TTL: 1 hour)
                │
                ▼
Frontend polls /api/verdict/result until complete
        │
        ▼
Renders: Verdict card + expandable debate transcript
```

---

## Backend Changes (app.py)

### 1. New dependencies (requirements.txt)
```
tradingagents @ git+https://github.com/TauricResearch/TradingAgents.git
langgraph>=0.2.0
```

### 2. New configuration
```python
# In app.py config section
VERDICT_CONFIG = {
    "llm_provider": "openrouter",
    "deep_think_llm": "deepseek/deepseek-v4-pro",
    "quick_think_llm": "meta-llama/llama-3.3-70b-instruct:free",
    "backend_url": "https://openrouter.ai/api/v1",
    "max_debate_rounds": 1,        # 1 round = faster, cheaper
    "max_risk_discuss_rounds": 1,
    "data_cache_dir": "/tmp/ta_cache",
    "results_dir": "/tmp/ta_results",
}
```

### 3. New API endpoint — trigger analysis
```python
@app.route("/api/verdict", methods=["POST"])
@login_required
def request_verdict():
    data = request.json or {}
    ticker = data.get("ticker", "").strip()
    timeframe = data.get("timeframe", "4H")
    
    if not ticker:
        return jsonify({"error": "ticker required"}), 400
    
    # Check Redis cache first
    cache_key = f"verdict:{ticker}:{timeframe}"
    if _redis_client:
        cached = _redis_client.get(cache_key)
        if cached:
            return jsonify(json.loads(cached))
    
    # Enqueue RQ job
    job = _rq_queue.enqueue(
        "app._run_verdict_analysis",
        ticker, timeframe,
        job_timeout=120,
        result_ttl=3600
    )
    
    return jsonify({"job_id": job.id, "status": "queued"})
```

### 4. RQ Worker function
```python
def _run_verdict_analysis(ticker, timeframe):
    """Runs TradingAgents deep analysis. Called by RQ worker."""
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    
    config = VERDICT_CONFIG.copy()
    ta = TradingAgentsGraph(debug=False, config=config)
    
    _, decision = ta.propagate(ticker, datetime.utcnow().strftime("%Y-%m-%d"))
    
    # Cache in Redis
    cache_key = f"verdict:{ticker}:{timeframe}"
    result = {
        "ticker": ticker,
        "verdict": decision,
        "timestamp": datetime.utcnow().isoformat()
    }
    if _redis_client:
        _redis_client.setex(cache_key, 3600, json.dumps(result))
    
    return result
```

### 5. Polling endpoint
```python
@app.route("/api/verdict/result", methods=["POST"])
@login_required
def verdict_result():
    data = request.json or {}
    job_id = data.get("job_id", "")
    ticker = data.get("ticker", "")
    
    # Check Redis cache
    cache_key = f"verdict:{ticker}:{timeframe}"
    if _redis_client:
        cached = _redis_client.get(cache_key)
        if cached:
            return jsonify(json.loads(cached))
    
    return jsonify({"status": "running"})
```

---

## Frontend Changes (index-v2-prototype.html)

### 1. New sidebar nav item
```html
<div class="nav-item" data-nav="verdict" onclick="setNav('verdict');showVerdict();">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
    </svg>
    <span>Verdict</span>
</div>
```

### 2. showVerdict() page — empty state
```
┌─────────────────────────────────────────────────┐
│  VERDICT                                         │
│  Deep analysis with multi-agent AI debate        │
│                                                   │
│  ┌─────────────────────────────────────────────┐  │
│  │  ⚡ Run a Deep Analysis                      │  │
│  │                                              │  │
│  │  DotVerse runs a virtual trading firm:       │  │
│  │  • 4 analysts study your asset               │  │
│  │  • 2 researchers debate bull vs bear case    │  │
│  │  • 3 risk managers argue position size       │  │
│  │  • Portfolio Manager makes the final call    │  │
│  │                                              │  │
│  │  Takes ~45 seconds. Costs 1 credit.          │  │
│  │                                              │  │
│  │  Enter a ticker to begin →                   │  │
│  └─────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### 3. showVerdict() — loaded state
```
┌─────────────────────────────────────────────────┐
│  VERDICT: BTC/USD · 4H                           │
│  Generated 2 minutes ago · DeepSeek V4 + Llama   │
│                                                   │
│  ┌─────────────────────────────────────────────┐  │
│  │  ▸ FINAL VERDICT                             │  │
│  │  ─────────────────────────────────────────── │  │
│  │  BUY · Confidence 72%                       │  │
│  │  Entry $82,312 · SL $79,009 · TP $90,406    │  │
│  │                                              │  │
│  │  "The bull case centers on strong technical  │  │
│  │   momentum — 5 of 7 indicators aligned.      │  │
│  │   Volume confirms conviction. However, the   │  │
│  │   bear flags tomorrow's CPI report as a risk. │  │
│  │   Recommend entering with 2% risk instead    │  │
│  │   of 5% until macro clears."                 │  │
│  └─────────────────────────────────────────────┘  │
│                                                   │
│  ▸ VIEW FULL DEBATE TRANSCRIPT (expandable)      │
│    ├── Market Analyst Report                     │
│    ├── News Analyst Report                       │
│    ├── Fundamentals Report                       │
│    ├── Bull vs Bear Debate                       │
│    ├── Risk Manager Debate                       │
│    └── Portfolio Manager Decision                │
│                                                   │
│  → Size this trade (navigates to Size tab)       │
└─────────────────────────────────────────────────┘
```

---

## Deployment Steps

1. `pip install tradingagents langgraph` — add to requirements.txt
2. Add `OPENROUTER_API_KEY` to Railway env vars
3. Add `VERDICT_CONFIG` to app.py
4. Add 3 API endpoints to app.py
5. Add `showVerdict()` function + sidebar nav item to index-v2-prototype.html
6. Deploy — RQ worker picks up the new job type automatically
7. Test with BTC 4H analysis

---

## Cost & Limits

| Metric | Value |
|--------|-------|
| Cost per analysis | ~$0.01 (DeepSeek V4 calls only, Llama is free) |
| Time per analysis | 35–45s |
| Daily at 50 analyses | $0.50/day |
| OpenRouter rate limit | 200 req/min (free tier), sufficient |
| Redis cache TTL | 1 hour — repeat analysis on same ticker is instant |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| LLM gives bad advice | Verdict is ADDITIVE to DotVerse signal, never overrides |
| OpenRouter down | Degrade gracefully — show "Verdict unavailable" |
| Cost spike with high usage | Rate-limit to 1 analysis per user per minute |
| LLM hallucinates data | TradingAgents fetches REAL yfinance data — LLM only interprets it |
