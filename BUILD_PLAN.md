# DotVerse Build Plan — Signal Engine + MT5 Integration

## The Goal
Strengthen signals by feeding live MT5 data back into the engine, and give every metric a feedback loop so the system learns from its own outcomes.

## PHASE 1 — Data Plumbing (unlocks everything else)

### 1.1 MT5 Auto-Outcome Logging ✅ DONE
**File**: app.py, mt5_confirm_order() ~line 7208
**What**: When EA reports CLOSE with P&L → auto-determine WIN/LOSS/BE → find matching SignalHistory → write outcome + exit_price + actual_pnl_r
**Status**: CODE WRITTEN but needs QA + Final Verifier before commit
**Depends on**: Nothing
**Unlocks**: WR per pattern, quality score, backtesting feedback

### 1.2 MT5 Live Spread → Signal Engine
**File**: app.py, get_analysis() ~line 3263-3800
**What**: get_analysis() already reads spread from mt5_state if available. Need to harden: ensure spread_cost field is always populated from EA push (not just estimated from SPREAD_TABLE), and add spread_quality score (tight/fair/wide) to analysis response.
**Changes**: ~20 lines in get_analysis()
**Depends on**: Nothing

### 1.3 MT5 Live Positions → Signal Dedup
**File**: app.py, mt5_state ~line 7456 + get_analysis() 
**What**: Before analyzing a ticker, check if user has an open MT5 position on that symbol. If yes → add `existing_position: {direction, entry, pnl}` to analysis response so the signal card can show "You're already in this trade" instead of recommending a duplicate.
**Changes**: New helper function + 5 lines in get_analysis()
**Depends on**: Nothing

## PHASE 2 — Signal Quality

### 2.1 Historical WR Per Pattern ✅ DONE + VERIFIED
**File**: app.py — GET /api/signals/winrate-by-pattern (line 12741)
**What**: Query SignalHistory WHERE outcome IS NOT NULL. Group by (ticker, timeframe, signal, trade_type). Compute win_rate, sample_size, avg_r. Minimum 5 samples. Skip BE from WR calc.
**Status**: Backend committed (14592f0) + frontend badge (Phase 2.5) implemented. Trade_type normalization added. Final Verifier approved.
**Depends on**: Phase 1.1 (needs outcomes logged)

### 2.2 Signal Quality Score (audit item 4)
**File**: app.py — new function compute_quality_score() called from get_analysis()
**What**: 0-100 composite score combining:
- Confidence (35%) — from get_analysis()
- Regime alignment (20%) — signal direction vs HTF bias
- SMC alignment (20%) — how many SMC patterns support vs oppose
- Spread efficiency (15%) — 1 - spread_cost/r1_distance
- Volume confirmation (10%) — from indBreakdown
**Response field**: `quality: {score: 0-100, label: POOR/FAIR/GOOD/EXCELLENT, breakdown: {confidence, regime, smc, spread, volume}}`
**Frontend**: Color ring next to confidence ring on signal card
**Depends on**: 1.2 (live spread for efficiency calc)

### 2.3 Regime Context Line (audit item 2)
**File**: app.py, get_analysis() return dict
**What**: One-sentence regime context string: "Market is trending → trend signals weighted higher" or "Ranging → mean-reversion bias" or "High volatility → SMC patterns active"
**Frontend**: One line of text below the signal card title
**Depends on**: Nothing separate — regime detection exists in get_analysis() already

### 2.4 Regime-Switching Weights (audit item 2 deeper)
**File**: app.py, get_analysis() — confidence computation section ~line 3400-3600
**What**: When regime=TRENDING, boost trend-following indicators (EMA alignment, HTF trend) by 1.5x. When RANGING, boost mean-reversion (RSI, StochRSI, BB). When HIGH_VOL, boost SMC patterns.
**Changes**: ~30 lines in the confidence vote-counting section
**Depends on**: 2.3 (regime detection)

### 2.5 WR Per Pattern Frontend Badge ✅ DONE + VERIFIED
**File**: static/index-v2-prototype.html — _sfFetchPatternWR function (line 8646)
**What**: dvFetchT call to winrate-by-pattern, caches all patterns, matches locally by key. Badge shows "WR: 65% (17)" with color thresholding. HOLD fallback, error handling, loading state, mobile responsive.
**Status**: Implemented. Final Verifier approved.
**Depends on**: 2.1 (backend endpoint)

## PHASE 3 — Adaptive + Optimization

### 3.1 Adaptive Confluence Threshold (audit item 5)
**File**: app.py — new endpoint + get_analysis() integration
**What**: Per-asset-class dynamic threshold. Bin signals by confluence bracket. Track WR per bracket. Optimal threshold = lowest bracket where WR >= 55%.
**Depends on**: Phase 2.1 (needs outcome data)

### 3.2 Per-Asset Parameter Optimization (audit item 8)
**File**: app.py — RQ job + get_analysis() integration
**What**: Weekly grid search per (asset_class, timeframe). Optimize RSI period, EMA periods, ATR mult, BB period. Store in OptimisationResult table. Signal engine uses optimized params when available.
**Depends on**: Phase 2.1 (needs outcome data)

### 3.3 Backtesting Feedback Loop (audit item 7)
**File**: app.py — APScheduler job + new endpoint
**What**: Weekly cron: query SignalHistory outcomes → compute strategy health metrics → flag degrading indicators → write to StrategyHealth model.
**Depends on**: Phase 2.1 (needs outcome data)

## PHASE 4 — Advanced (deferred)

### 4.1 ML Confidence Calibration (audit item 3)
**What**: Isotonic Regression on historical outcomes to calibrate confidence.
**Depends on**: 50+ labeled outcomes per user (time)

### 4.2 Alternative Data Pipeline (audit item 6)
**What**: On-chain metrics, options flow, social sentiment multiplexer.
**Depends on**: Paid API keys, monetization
