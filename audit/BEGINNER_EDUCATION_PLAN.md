# DotVerse — Beginner Education Plan
## Mode: HIGH (content/copy writing, not visual design)

---

## Principle
Every feature must answer: **What is this? Why do I need it? How do I use it?**
No jargon without a plain-English explanation alongside it.

---

## 1. BACKTEST PAGE (Pipeline > Track Record → rename to "Backtest")

### Current state
- No introduction. User lands on a page with ticker buttons, timeframe pills, and "Run Backtest" button.
- Results show "Win Rate", "Profit Factor", "Sharpe", "Expectancy" — zero explanation.
- Beginner has no idea what this page does or why they should use it.

### Proposed changes

**A. Banner at top (appears when page loads):**
```
┌─────────────────────────────────────────────────────────────┐
│  WHAT IS BACKTESTING?                                       │
│                                                             │
│  Before you risk real money on a signal, backtesting lets   │
│  you see how that same signal would have performed over      │
│  the last 5 years of market data. Think of it as a time     │
│  machine for your trade idea.                                │
│                                                             │
│  HOW TO USE IT:                                              │
│  1. Pick a ticker (e.g. BTC)                                │
│  2. Pick a timeframe (e.g. 4H)                              │
│  3. Click "Run Backtest"                                     │
│  4. Read the results — focus on:                             │
│     • Win Rate: above 55% is good                           │
│     • Profit Factor: above 1.2 means you make more than     │
│       you lose                                               │
│     • Expectancy: positive = strategy has an edge            │
│                                                             │
│  If all three are in the green → the signal is worth taking. │
│  If any are red → consider skipping this trade.              │
└─────────────────────────────────────────────────────────────┘
```

**B. Inline explainers on each result card:**
- "Win Rate" → mouse hover shows: "How often this signal would have won. Example: 60% means 6 out of 10 trades hit their target."
- "Profit Factor" → hover: "Total wins divided by total losses. Above 1.0 means you made more than you lost."
- "Sharpe Ratio" → hover: "Risk-adjusted return. Above 1.0 is good. Below 0.5 means the returns aren't worth the volatility."
- "Expectancy" → hover: "Average $ you make or lose per $1 risked. Positive number = long-term profit."
- "Max Drawdown" → hover: "The biggest dip your account would have taken if you followed this signal. Helps you decide if you can stomach the ride."

**C. After backtest completes, plain-English verdict banner:**
- Green: "This strategy has a proven edge. Consider taking this trade with confidence."
- Amber: "Mixed results — the strategy could work but has risks. Use smaller position size."
- Red: "This strategy underperformed historically. We recommend skipping this trade."

**D. "What this does NOT tell you" disclaimer:**
"Past performance does not guarantee future results. Markets change. Use backtest results as one input — not the only one."

**Lines to change:** `showBacktest()` function, backtest result rendering

---

## 2. UNDERSTAND PAGE

### Current state
- Shows signal verdict, chart, indicators, RSI divergence, MTF grid.
- No explanation of what any indicator means for a beginner.

### Proposed changes

**A. "What you're looking at" intro when signal loads:**
```
┌──────────────────────────────────────────────────┐
│  This page explains WHY DotVerse gave this        │
│  signal. Each section below breaks down one piece │
│  of the analysis so you understand the reasoning. │
│                                                   │
│  TOP: The signal verdict + key levels             │
│  CHART: Price action with entry/SL/TP lines       │
│  INDICATORS: What 7 tools saw (RSI, EMA, etc.)    │
│  CONFLUENCE: How many indicators agree             │
│  MULTI-TF: What other timeframes say               │
└──────────────────────────────────────────────────┘
```

**B. Indicator grid — each card gets plain-English name + "what this means":**
Current labels like "RSI" → change to:

- **RSI (Overbought/Oversold)**
  "Measures if price has moved too far too fast. Above 70 = overbought (might drop). Below 30 = oversold (might rise)."
  
- **MACD (Trend Strength)**
  "Compares short-term vs long-term price momentum. When the blue line crosses above the orange line — bullish. Opposite = bearish."

- **Bollinger Bands (Price Range)**
  "Shows if price is near a high or low extreme. Price near the top band = expensive. Near bottom band = cheap."

- **Supertrend (Trend Direction)**
  "Simple yes/no: is the trend up (green) or down (red)? Follow the trend — don't fight it."

- **Volume**
  "Shows if people are actually trading this. High volume = strong conviction behind the move. Low volume = weak move."

**C. Confluence panel — add beginner explanation:**
"Confluence means 'agreement.' If 5 of 7 indicators point the same direction, that's strong. If only 2 agree, that's weak. DotVerse requires at least 65% agreement (4 out of 6) before showing a signal. Think of it like getting a second, third, and fourth opinion before making a decision."

---

## 3. SIZE PAGE

### Current state
- Many inputs, coaching panel, presets. But coaching shows AFTER user fills values.
- Beginner doesn't know where to start.

### Proposed changes

**A. Always-visible intro (above coaching panel):**
```
┌──────────────────────────────────────────────────┐
│  POSITION SIZING — what is this?                  │
│                                                   │
│  Before you trade, you decide:                     │
│  • How much of your account to risk (Risk %)       │
│  • Where to enter and exit (Entry, SL, TP)         │
│                                                   │
│  The calculator then tells you exactly:            │
│  • How much to buy (position size)                 │
│  • Your dollar loss if the trade goes wrong        │
│  • Your potential profit if it goes right          │
│                                                   │
│  Why? Because guessing your size = gambling.       │
│  Calculating your size = trading.                  │
└──────────────────────────────────────────────────┘
```

**B. Risk % preset explainers on hover:**
- CONSERVATIVE: "1% risk means on a $10,000 account you lose $100 max per trade. You can lose 100 trades in a row before blowing up. Good for beginners."
- STANDARD: "2% risk means $200 max loss on $10,000. Pro traders typically use 1-2%."
- AGGRESSIVE: "5% risk means $500 max loss on $10,000. High risk — only 20 losing trades to blow up. Not recommended for beginners."

**C. "Why 1-2%?" expandable section:**
"The 1% rule exists because even the best traders lose 40% of the time. At 1% risk, you survive long losing streaks. At 5% risk, 20 losses wipe you out. Risk management is the ONLY thing you control — you can't control the market, but you control how much you lose."

---

## 4. ACT PAGE

### Current state
- Shows trade execution options, trailing stops, etc. Jargon-heavy.

### Proposed changes

**A. Header explainer:**
"ACT is the final step — this is where you place your trade. Only proceed if you've completed the previous three steps (Understand, Size). If you skipped any step, go back — never trade without knowing your exit plan."

**B. "Market Execution" explainer:**
"This is the simplest way to trade. Your order fills immediately at the current market price. Use this when you want to enter NOW — no waiting."

**C. "Limit Order" explainer:**
"Your order only fills at a specific price you set (or better). Use this when you want a precise entry — but it might not fill if the market doesn't reach your price."

**D. "Stop Loss" explainer:**
"Your safety net. If the price moves against you, this automatically closes your trade at a fixed loss. Never trade without a stop loss. The calculator (Size tab) already calculated yours — use that number."

---

## 5. GLOBAL — TOOLTIPS ON ALL JARGON TERMS

Add `title` attributes (browser-native hover tooltips) on these terms across the entire app:

| Term | Tooltip |
|------|---------|
| RSI | "Relative Strength Index — measures if price is overbought (>70) or oversold (<30). Values outside these ranges suggest a reversal." |
| EMA | "Exponential Moving Average — smooths recent price data to show the trend direction. Short EMA above long EMA = uptrend." |
| ATR | "Average True Range — measures market volatility. Big ATR = big price swings = wider stops needed." |
| MACD | "Moving Average Convergence Divergence — shows momentum. Blue line crossing above signal line = bullish momentum." |
| R:R (Risk/Reward) | "How much you risk vs how much you can gain. 1:2 means you risk $1 to make $2. Only take trades with at least 1:1.5 R:R." |
| Confluence | "When multiple indicators agree on the same direction. Higher confluence = stronger signal." |
| Drawdown | "The peak-to-trough drop in your account value. If you start with $10,000 and drop to $9,000, that's a 10% drawdown." |
| Kelly % | "A formula that calculates the mathematically optimal bet size. Half-Kelly is the safer version used by most pros." |
| Profit Factor | "Gross profit divided by gross loss. 1.5 means you make $1.50 for every $1.00 you lose." |
| Expectancy | "Average amount you make per dollar risked. Positive = profitable long-term. Negative = losing strategy." |

---

## Priority Order (what to fix first)

| Priority | Page | Why |
|----------|------|-----|
| 1 | Backtest | Currently unusable for beginners — no explanation at all |
| 2 | Understand | Beginner spends most time here — needs to learn from it |
| 3 | Size | Good coaching exists but doesn't teach WHY |
| 4 | Act | Needs safety warnings and order type explainers |
| 5 | Global tooltips | Make every jargon term explainable on hover |

---

## What this does NOT include

- No visual redesign (no colors, layout, spacing)
- No branding changes (no logo, slogan, AI removal)
- No new features — only educational text additions
