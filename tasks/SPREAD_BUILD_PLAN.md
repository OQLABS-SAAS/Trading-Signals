# DotVerse — Spread Awareness Build Plan
### Date: 2026-05-16
### Principle: Every spread-adjusted number shows the raw value, adjusted value, adjustment amount, and one plain-English sentence explaining what caused the difference and what it means for this specific trade.

---

## Why This Exists

The spread is the broker's fee on every trade, paid at entry. DotVerse currently:
- Shows R:R calculated from clean price levels (pre-spread) — optimistic
- Shows net profit in the calculator without deducting spread — misleading
- Has a flat 0.2% `fee_adj` in the backend that approximates spread but is never surfaced to the trader

This means a beginner sees "R:R 1:2" and "net +$109" but actually gets R:R 1:1.7 and +$89 net.
That gap between what DotVerse shows and what the trader gets erodes trust and fails the founding principle: DotVerse educates traders about every number it shows.

---

## Design Standard (applies to every step)

**Rule:** Any number adjusted for spread must display:
1. The **adjusted value** — prominently (this is what the trader uses)
2. The **raw value** — secondary, greyed out
3. The **spread cost** — how much was deducted/added
4. A **plain-English sentence** — what spread is, why it affected this number, in this specific context

**Pattern (expandable):**
```
+$96 net  ←  adjusted
  ↳ Raw: +$109 · Spread cost: $13
  [Why?▾]  The spread is the broker's fee on this trade — you pay it the
           moment you enter, not when you exit. This is why your trade
           starts slightly in the red.
```

The `[Why?▾]` uses the same `<details>/<summary>` pattern as the automation guides. Always collapsed by default. Always readable expanded.

---

## Data Sources — Three Tiers (in priority order)

### Tier 1 — Live from MT5 EA (ideal, requires EA change)
The MT5 EA already pushes account + position data every 5s to `/api/mt5/heartbeat`.
Add one field to the EA's push payload:

**MQL5 addition (EA side — one line):**
```mql5
"spread": (double)SymbolInfoInteger(symbol, SYMBOL_SPREAD) / 10.0  // in pips
```

Backend stores this in `mt5_state[user_id]["spread"][symbol]`.
`_get_spread(ticker, asset_type)` reads from there first, falls back to Tier 2.

### Tier 2 — Hardcoded typical spread table (fallback when MT5 not connected)
```python
SPREAD_TABLE = {
    # Forex majors (pips)
    "EURUSD=X": 1.5, "GBPUSD=X": 2.0, "USDJPY=X": 1.5, "AUDUSD=X": 2.0,
    "USDCHF=X": 2.0, "USDCAD=X": 2.5, "NZDUSD=X": 2.5,
    # Forex minors (pips)
    "EURGBP=X": 2.5, "EURJPY=X": 2.5, "GBPJPY=X": 3.5,
    # Crypto (% of price)
    "BTC-USD": 0.05, "ETH-USD": 0.07, "BNB-USD": 0.10,
    # Indices (points)
    "^GSPC": 0.5, "^NDX": 1.0, "^DJI": 2.0, "^FTSE": 1.5,
    # Commodities (price units)
    "GC=F": 0.5, "SI=F": 0.030, "CL=F": 0.03,
    # Stocks (% of price — variable, use 0.05% as floor)
    "_default_stock": 0.05,
    "_default_crypto": 0.10,
    "_default_forex": 3.0,
    "_default_index": 1.0,
    "_default_commodity": 0.1,
}
```

### Tier 3 — Current flat estimate (only if tiers 1 and 2 both fail)
The existing `fee_adj = entry * 0.002` stays as absolute fallback.
But it must be labelled as an estimate, not a precise spread.

---

## Build Steps

### Step A — `_get_spread(ticker, asset_type, entry)` helper in app.py

New function. Returns spread in price units (dollars, pips converted to price, points).

```python
def _get_spread(ticker, asset_type, entry=1.0):
    """Return spread in price units for the given instrument.
    Priority: Tier 1 (live MT5) → Tier 2 (table) → Tier 3 (flat estimate).
    Returns: (spread_price_units, source_label)
    """
```

Logic:
- Tier 1: check `mt5_state` for `spread[symbol]` — convert pips to price units
- Tier 2: lookup `SPREAD_TABLE` by ticker, then by `_default_{asset_type}`
- Tier 3: `entry * 0.002 / 2` (half of round-trip as one-way entry cost)
- Always returns `(float, "live" | "estimated" | "approximate")`

**Pip to price conversion for forex:**
- `spread_price = spread_pips * pip_size`
- Pip size: 0.0001 for most pairs, 0.01 for JPY pairs

### Step B — Spread-adjusted R:R in `get_analysis()`

Replace current R:R calculation:
```python
# Current (pre-spread):
rr1 = (tp1 - entry) / (entry - sl)  # BUY

# New (spread-adjusted):
spread_cost, spread_source = _get_spread(ticker, asset_type, entry)
rr1_raw = (tp1 - entry) / (entry - sl)
rr1_adj = (tp1 - entry - spread_cost) / (entry - sl + spread_cost)
```

Response dict additions:
```python
"rr1":          round(rr1_adj, 2),   # what the card shows (adjusted)
"rr1_raw":      round(rr1_raw, 2),   # for display alongside
"spread_cost":  round(spread_cost, 6),
"spread_source": spread_source,       # "live" | "estimated" | "approximate"
"spread_pips":  round(spread_cost / pip_size, 1) if forex else None,
```

Same for rr2, rr3.

### Step C — Signal card shows spread (frontend)

On the signal card, below the R:R row, add one new line:

**When spread is live (Tier 1):**
```
Spread: 1.5 pips live  ·  Adj. R:R 1:1.4  (raw 1:1.5)
```

**When spread is estimated:**
```
Spread: ~1.5 pips (est.)  ·  Adj. R:R 1:1.4  (raw 1:1.5)
```

With `<details>/<summary>` education panel:
> **What is spread?**
> The spread is the difference between the buy price and sell price. Your broker charges this as a fee at entry. On this trade, 1.5 pips of spread costs you $15 on a standard lot, reducing your net reward from +$150 to +$135 at TP1. Your R:R of 1:1.5 becomes 1:1.4 in real money.

### Step D — Scalp guard in `get_analysis()`

If trade type is scalping and `spread_cost > 0.25 * (tp1 - entry)`:
- Signal downgrades: `signal = "HOLD"`
- Reason: `"Spread too wide for scalp — spread is {pct}% of TP1 distance"`
- Plain-English coaching card on frontend:
  > *Not recommended for scalping right now. Your TP1 target is X pips away. The spread on this pair is Y pips — that's Z% of your target consumed before price moves a single pip in your favour. Scalping only works when spread is a small fraction of the target. Wait for tighter market conditions or switch to the 1H timeframe for a wider target.*

### Step E — Calculator TP rows deduct spread

In `szCalc()` (frontend) and in the net profit calculation:

Each TP row currently shows:
```
TP1: +$109 net
```

Changes to:
```
TP1: +$96 net
     Raw +$109 · Spread cost $13
     [Why?▾] The spread is the broker's fee...
```

The spread cost per TP row:
- `spread_dollar = spread_price_units * lots * contract_size`
- Deducted from gross profit on each TP

### Step F — News filter coaching updated

When the news filter fires (automation workers), the Telegram message and in-app coaching say:

> *News event in X minutes. DotVerse has paused new entries. Note: spread typically widens 3–10× during high-impact news — your displayed SL distance may not protect you from a spike. If you have open trades, your displayed SL of 10 pips could be hit by spread alone during the announcement.*

### Step G — EA heartbeat extension (Tier 1 activation)

**File: EA (MQL5) — one addition to the heartbeat JSON payload:**
```mql5
// In the section that builds the JSON payload for /api/mt5/heartbeat
// Add after existing symbol info:
"spread": (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) / 10.0,
```

**Backend: `/api/mt5/heartbeat` handler — store spread:**
```python
if "spread" in body:
    mt5_state[user_id]["spread"] = mt5_state[user_id].get("spread", {})
    mt5_state[user_id]["spread"][body.get("symbol", "")] = float(body["spread"])
```

**`_get_spread()` Tier 1 path:**
```python
with mt5_state_lock:
    for uid, state in mt5_state.items():
        spreads = state.get("spread", {})
        symbol_key = _mt5_symbol(ticker, asset_type)
        if symbol_key in spreads:
            return spreads[symbol_key] * pip_size, "live"
```

---

## Implementation Order

| Step | File(s) | Scope | Blocker |
|------|---------|-------|---------|
| A | app.py | New helper function | None |
| B | app.py | Modify get_analysis() | Step A |
| C | index-v2-prototype.html | Signal card UI | Step B |
| D | app.py | Scalp guard logic | Step B |
| E | index-v2-prototype.html | Calculator TP rows | Step B |
| F | app.py | News filter coaching | Step A |
| G | EA + app.py | Tier 1 live spread | Steps A-F stable |

Steps A–F are fully self-contained — they work with the spread table (Tier 2) immediately.
Step G activates Tier 1 live data and makes every number more precise.
Start with A, verify each step in browser before proceeding to the next.

---

## Education Strings (for reference when building C, D, E, F)

**What is spread (general):**
> The spread is the difference between the price you buy at and the price the market values your position at immediately after entry. Your broker charges this as a fee the moment you enter a trade — not when you exit. This is why every trade starts slightly in the red before price moves in your favour.

**Why R:R is adjusted:**
> The displayed R:R is calculated from clean price levels. The adjusted R:R deducts your spread cost from the reward and adds it to the risk — because that is what your account actually experiences. A signal with raw R:R 1:2 and a 2-pip spread on a 10-pip SL becomes real R:R 1:1.7.

**Why net profit is lower:**
> The raw profit assumes you entered at exactly the signal price. In reality you entered at the ask price — the signal price plus the spread. This $X difference is the spread cost, and it comes out of your profit on every winning trade.

**Scalp guard:**
> Scalping only works when the spread is a tiny fraction of your target. If the spread is 30%+ of your TP1 distance, you need an immediate and sustained move just to overcome the entry cost. That is a low-probability trade. DotVerse will not recommend scalping when market conditions make it structurally difficult.

---

## Non-Goals (excluded and why)

- Dynamic spread feeds from external APIs (Oanda, FXCM): adds external dependency, latency, and auth complexity. Tier 2 table is accurate enough for education.
- Per-minute spread tracking: unnecessary — spread matters at entry, not continuously.
- Spread comparison between brokers: out of scope for DotVerse.
