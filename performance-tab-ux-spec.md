# Performance Tab UX Improvements — Design Spec

Target file: `/Users/oq/Documents/trading-signals-saas/static/index-v2-prototype.html`
Scope: `showPerformance()` function (~lines 12059–12606) and `window._dvGuide` object (~lines 21285+)

## Overview

The Performance tab has all the right data but lacks:
- Plain-English section headers explaining what each section is for
- Proper empty states with "what to do next" instructions
- Beginner-friendly tooltips on every metric

This spec covers all three additions. The coding agent should read each item below and insert the exact text at the location described.

---

## 1. SECTION HEADERS — Plain-English Descriptions

Each section currently has a `<div class="perf-card-head">` with a `<span class="perf-card-title">`. The spec adds a plain-English description line immediately below each card head, inside the card body.

### 1.1 Page-level sub-header (already exists at line 12304)

Current:
```
<div style="font-size:10px;color:rgba(237,232,216,.35);margin:-8px 0 12px;line-height:1.5;">
  Your trading track record · PnL curve, drawdown, stats, and monthly heatmap.
  Benchmark: ${_settBench==='spy'?'S&P 500':_settBench==='nq100'?'NASDAQ 100':_settBench==='btc'?'BTC':'Custom'}.
  Log trade outcomes below to populate real performance data.
</div>
```
Replace with:
```
<div style="font-size:10px;color:rgba(237,232,216,.35);margin:-8px 0 12px;line-height:1.5;">
  This is your trading report card. It answers three questions:
  <strong style="color:rgba(237,232,216,.5);">Are you making money?</strong> (PnL curve, expectancy),
  <strong style="color:rgba(237,232,216,.5);">How risky is your strategy?</strong> (drawdown, Sharpe),
  and <strong style="color:rgba(237,232,216,.5);">Where do you trade most?</strong> (asset breakdown, monthly heatmap).
  Benchmark: ${_settBench==='spy'?'S&P 500':_settBench==='nq100'?'NASDAQ 100':_settBench==='btc'?'BTC':'Custom'}.
</div>
```

### 1.2 Performance Stats card (line ~12215, _statsCard)

Current card-head:
```
<span class="perf-card-title">Performance Stats</span>
<span class="perf-card-sub">${_ptotal} closed trades · real verified data</span>
```

Below the four metric boxes (Sharpe/WinRate/ProfitFactor/Expectancy grid), add a description line. Insert AFTER the closing `</div>` of the 4-column grid (after line 12242) and before the closing `</div>` of perf-card:

Add:
```
<div style="padding:0 16px 12px;font-size:11px;color:rgba(237,232,216,.4);line-height:1.6;">
  <strong style="color:rgba(237,232,216,.55);">What are these?</strong>
  These four numbers tell you if your strategy has a real edge.
  <strong style="color:rgba(93,232,160,.65);">Sharpe</strong> = are your returns worth the risk?
  <strong style="color:rgba(93,232,160,.65);">Win rate</strong> = how often do you win?
  <strong style="color:rgba(93,232,160,.65);">Profit factor</strong> = how much bigger are your wins than losses?
  <strong style="color:rgba(93,232,160,.65);">Expectancy</strong> = on average, how many R's do you make per trade?
</div>
```

### 1.3 PnL / Equity Curve card (line ~12315)

Current card-head:
```
<span class="perf-card-title">PnL / Equity Curve</span>
<span class="perf-card-sub">...trades over ...days</span>
```

After the canvas element (`<canvas id="perfEqChart"...>`) and before the closing `</div>` of perf-card, add:

```
<div style="padding:0 16px 12px;font-size:11px;color:rgba(237,232,216,.4);line-height:1.6;">
  This chart shows your cumulative profit over time, measured in <strong style="color:rgba(237,232,216,.5);">R-multiples</strong>.
  One "R" = your risk per trade. If you risk $100 per trade and the line reads +5.2R,
  you are up $520. The green line is your actual PnL. The dashed gold line is your
  all-time high watermark — drawdown is the distance below it.
</div>
```

### 1.4 Drawdown card (line ~12253, _ddCard)

Current card-head:
```
<span class="perf-card-title">Drawdown</span>
<span class="perf-card-sub">Max: ${_ddMax}% · Peak equity: ${_ddPeak.toFixed(2)}</span>
```

After the summary stats row (after line 12262, closing `</div>` of the 4-stat flex row) and before closing `</div>` of perf-card, add:

```
<div style="padding:0 16px 12px;font-size:11px;color:rgba(237,232,216,.4);line-height:1.6;">
  <strong style="color:rgba(237,232,216,.55);">Drawdown</strong> measures how far your account has fallen from its peak.
  Think of it as the "pothole depth" on your trading road.
  Under 5% is normal. Over 20% means your risk per trade may be too high.
  The chart shows your equity (green) and the drawdown dips (red shaded areas).
</div>
```

### 1.5 Monthly Returns Heatmap (line ~12285, _hmHtml)

Current card-head:
```
<span class="perf-card-title">Monthly Returns Heatmap</span>
<span class="perf-card-sub">R-multiples by month · green = profit, red = loss</span>
```

After the closing `</table>` and before closing `</div></div>` of the perf-card wrapper, add:

```
<div style="padding:8px 12px 0;font-size:11px;color:rgba(237,232,216,.4);line-height:1.6;border-top:1px solid var(--bd);">
  Each cell is one month. <strong style="color:#5de8a0;">Green</strong> = profitable month.
  <strong style="color:#e05555;">Red</strong> = losing month. A dot (·) means no trades that month.
  Look for patterns — do you lose money in the same months every year?
  That might tell you when to trade smaller or sit out.
</div>
```

### 1.6 Recent Signal Activity card (line ~12323)

No change to card-head. After the `${tradeRows}` content and before closing `</div>` of perf-card, add:

```
<div style="padding:0 16px 12px;font-size:11px;color:rgba(237,232,216,.4);line-height:1.6;border-top:1px solid var(--bd);">
  These are your most recent signals. For each one, click <strong style="color:rgba(201,168,76,.8);">Log Result</strong>
  to record whether it was a WIN, LOSS, or breakeven. The more outcomes you log,
  the more accurate your Performance Stats become. Expired signals are dimmed —
  they can still be logged.
</div>
```

### 1.7 Signals by Asset Class card (line ~12331)

Current card-head:
```
<span class="perf-card-title">Signals by Asset Class</span>
```
(sub-head is missing — only title)

Add sub-head:
```
<span class="perf-card-title">Signals by Asset Class</span>
<span class="perf-card-sub">Where your trades are concentrated</span>
```

After the `${assetRows}` and before closing `</div>` of perf-card, add:

```
<div style="padding:0 16px 12px;font-size:11px;color:rgba(237,232,216,.4);line-height:1.6;border-top:1px solid var(--bd);">
  This shows what types of assets your signals target.
  <strong style="color:rgba(237,232,216,.55);">Diversification reduces risk.</strong>
  If one asset class dominates, a single market event can hurt your whole portfolio.
  Aim to spread your signals across 2–3 different asset types.
</div>
```

### 1.8 Trade Expectancy card (line ~12335)

Current card-head:
```
<span class="perf-card-title">Trade Expectancy</span>
<span class="perf-card-sub">...based on X closed trades...</span>
```

After the `${_expCard}` and before closing `</div>` of perf-card, add:

```
<div style="padding:0 16px 12px;font-size:11px;color:rgba(237,232,216,.4);line-height:1.6;border-top:1px solid var(--bd);">
  <strong style="color:rgba(237,232,216,.55);">Expectancy is the single most important number in trading.</strong>
  It tells you how much you expect to earn (or lose) per trade, on average.
  Positive = profitable strategy. Negative = losing strategy.
  Even a 40% win rate can be profitable if your wins are 3x bigger than your losses.
</div>
```

### 1.9 Your Targets card (line ~12344)

Current card-head:
```
<span class="perf-card-title">Your Targets</span>
<span class="perf-card-sub">From Settings → Performance</span>
```

After the 4-column grid (after line 12370, closing `</div>` of the grid) and before closing `</div>` of perf-card, add:

```
<div style="padding:0 16px 12px;font-size:11px;color:rgba(237,232,216,.4);line-height:1.6;border-top:1px solid var(--bd);">
  You set these goals in Settings → Performance. They are your personal benchmarks.
  <strong style="color:#c9a84c;">Gold numbers</strong> are your targets.
  <strong style="color:#5de8a0;">Green numbers</strong> mean you are hitting or beating them.
  Adjust targets as your strategy improves.
</div>
```

### 1.10 Confidence Calibration card (line ~12373)

Add a plain-English header inside the card, above the ECE stat grid. Insert RIGHT AFTER the opening `<div style="display:grid;grid-template-columns:1fr 2fr;gap:14px;padding:6px 0;">` (line ~12416):

```
<div style="grid-column:1/-1;padding:0 0 8px;font-size:11px;color:rgba(237,232,216,.4);line-height:1.6;">
  <strong style="color:rgba(237,232,216,.55);">Calibration answers: "When DotVerse says 80% confident, does it really win 80% of the time?"</strong>
  If your signals say 80% but only win 55% of the time, they are overconfident — calibration fixes that.
  The green bars show actual win rates per confidence bin. The gold line is what they SHOULD be after correction.
</div>
```

---

## 2. EMPTY STATES — Messages and Triggers

Each empty state tells the user exactly what is missing and what to do about it.

### 2.1 Performance Stats card — when _ptotal === 0 (no closed trades)

Trigger: `_ptotal === 0` (the _statsCard evaluates to empty string `''`)

What to insert (replace the empty-string case of _statsCard):
```
<div class="perf-card" style="margin-bottom:16px;">
  <div class="perf-card-head">
    <span class="perf-card-title">Performance Stats</span>
    <span class="perf-card-sub">No closed trades yet</span>
  </div>
  <div style="padding:24px 16px;text-align:center;color:rgba(237,232,216,.3);font-size:12px;line-height:1.8;">
    <div style="font-size:32px;margin-bottom:10px;">&#x1F4CA;</div>
    <div style="color:rgba(237,232,216,.5);font-size:13px;margin-bottom:8px;">
      <strong>Your performance dashboard is waiting for data.</strong>
    </div>
    <div>
      These stats (Sharpe ratio, win rate, profit factor, expectancy) need
      <strong style="color:rgba(201,168,76,.7);">closed trades with logged outcomes</strong>
      to calculate real numbers.
    </div>
    <div style="margin-top:10px;">
      <strong style="color:rgba(93,232,160,.6);">How to fix this:</strong>
      Scroll to Recent Signal Activity below and click
      <strong style="color:rgba(201,168,76,.8);">Log Result</strong>
      on any signal that has completed. Once you log 30+ outcomes, these stats unlock.
    </div>
  </div>
</div>
```

### 2.2 PnL / Equity Curve — when no PnL data

Already handled in canvas (lines 12550–12554), but the text should be improved.

Current canvas fallback text:
```
'No PnL data yet — log trade outcomes below'
'Use Log Result buttons in Recent Signal Activity'
```

Change to:
```
'No profit data yet — log trade outcomes to build your curve'
'Click Log Result on completed signals in Recent Activity below'
```

### 2.3 Drawdown card — when no snapshots (_ddSnaps.length < 2)

Already handled in canvas (lines 12597–12602), but improve the canvas fallback text.

Current:
```
'No equity snapshots yet'
'Snapshots populate as trades close'
```

Change to:
```
'Not enough data for a drawdown chart'
'Drawdown appears after your first few closed trades'
```

### 2.4 Monthly Heatmap — when no data (already has empty state at line 12327)

Current empty state:
```
'No closed trades yet — monthly returns will populate as you log outcomes'
```

Replace with:
```
<div style="padding:24px 16px;text-align:center;color:rgba(237,232,216,.3);font-size:12px;line-height:1.8;">
  <div style="font-size:28px;margin-bottom:8px;">&#x1F4C5;</div>
  <div style="color:rgba(237,232,216,.5);font-size:13px;margin-bottom:8px;">
    <strong>No monthly performance data yet.</strong>
  </div>
  <div>
    The heatmap builds as you log trade outcomes. Each closed trade
    contributes to the month it was taken. After a few months of
    active trading, you will see green and red patterns emerge.
  </div>
  <div style="margin-top:10px;">
    <strong style="color:rgba(93,232,160,.6);">How to fix this:</strong>
    Log outcomes on your past signals using the Log Result buttons.
    Trades from previous months still count — they will appear in their
    correct month column.
  </div>
</div>
```

### 2.5 Recent Signal Activity — when no signals (line 12134 already has one)

Current empty state:
```
'No signals yet. Run your first analysis in the UNDERSTAND tab.'
```

Replace with:
```
<div style="padding:20px 16px;text-align:center;color:rgba(237,232,216,.3);font-size:12px;line-height:1.8;">
  <div style="font-size:28px;margin-bottom:8px;">&#x1F50D;</div>
  <div style="color:rgba(237,232,216,.5);font-size:13px;margin-bottom:8px;">
    <strong>No signals recorded yet.</strong>
  </div>
  <div>
    Signals appear here after you run an analysis on a ticker.
    Each signal includes the direction, entry price, stop loss,
    and confidence score.
  </div>
  <div style="margin-top:10px;">
    <strong style="color:rgba(93,232,160,.6);">What to do:</strong>
    Go to the <strong style="color:rgba(201,168,76,.8);">UNDERSTAND tab</strong>,
    pick a ticker (e.g., BTCUSDT, AAPL), choose a timeframe,
    and click Analyse. Your signal will appear here when it fires.
  </div>
</div>
```

### 2.6 Signals by Asset Class — when no signals (line 12109 already has one)

Current empty state:
```
'No signals yet — run your first analysis.'
```

Replace with:
```
<div style="padding:16px 0;text-align:center;color:rgba(237,232,216,.3);font-size:12px;line-height:1.8;">
  No signals yet — this breakdown will show where your trades are concentrated.
  <div style="margin-top:8px;">
    <strong style="color:rgba(201,168,76,.7);">To get started:</strong>
    run an analysis in the UNDERSTAND tab on any ticker.
  </div>
</div>
```

### 2.7 Trade Expectancy card — when stats not ready (line 12161–12169, _expCard not-ready branch)

Current (already good, but could be improved):
```
`<div style="font-size:11px;color:rgba(237,232,216,.4);margin-top:10px;line-height:1.7;">
  Log <strong style="color:rgba(201,168,76,.8);">${30-stats.sample_size} more trade outcomes</strong>
  using the Log Result buttons in Recent Signal Activity below.
  DotVerse will then calculate your real expectancy — the most important
  number in trading. Positive expectancy means your strategy makes money
  over time.
</div>`
```

Replace the last sentence with:
```
<strong style="color:rgba(93,232,160,.65);">Positive expectancy</strong>
means your strategy is predicted to make money over time, even if individual
trades lose. Negative expectancy means you are expected to lose money long-term,
regardless of recent wins. This is the single most important number in your
trading career.
```

### 2.8 Your Targets — "no data yet" states

Within the targets card, these already show "no data yet" and "target only" where applicable (lines 12353, 12358). Those are adequate. No change needed.

### 2.9 Calibration card — when no data (calibData is null or error; already returns '')

Trigger: `!calibData || calibData.error` → currently returns `''` (line 12374)

Replace `return '';` with an empty state card:
```
return '<div class="perf-card" style="margin-top:14px;">'
  +'<div class="perf-card-head">'
    +'<span class="perf-card-title">&#x1F4CA; Confidence Calibration</span>'
    +'<span class="perf-card-sub">Isotonic regression — corrects overconfident signals</span>'
  +'</div>'
  +'<div style="padding:24px 16px;text-align:center;color:rgba(237,232,216,.3);font-size:12px;line-height:1.8;">'
    +'<div style="font-size:28px;margin-bottom:8px;">&#x1F3AF;</div>'
    +'<div style="color:rgba(237,232,216,.5);font-size:13px;margin-bottom:8px;">'
      +'<strong>No calibration data available.</strong>'
    +'</div>'
    +'<div>'
      +'Calibration corrects your confidence scores so that "80% confident" '
      +'really means 80% of those signals win. It needs 50+ labeled trade '
      +'outcomes to produce reliable corrections.'
    +'</div>'
    +'<div style="margin-top:10px;">'
      +'<strong style="color:rgba(93,232,160,.6);">How to fix this:</strong> '
      +'Log trade outcomes (WIN/LOSS/BE) using the Log Result buttons in '
      +'Recent Signal Activity. When you have enough data, click '
      +'<strong style="color:rgba(201,168,76,.8);">Sync Labels</strong> '
      +'and your calibration will appear.'
    +'</div>'
  +'</div>'
+'</div>';
```

### 2.10 Overview mini-cards — when total === 0 (no signals at all)

Lines 12306–12309 already show "—" and "Run your first analysis to start tracking here". Improve them:

For SIGNALS card (line 12306):
Current trend text: `'Run your first analysis to start tracking here'`
Replace with: `'Go to UNDERSTAND tab → pick a ticker → click Analyse'`

For AVG CONF card (line 12307):
Current trend text: `'Run your first analysis to start tracking here'`
Replace with: `'Confidence appears after you run your first analysis'`

For HIGH CONF card (line 12308):
Current trend text: `'Run your first analysis to start tracking here'`
Replace with: `'CONFIRMED signals appear here after analysis'`

For BUY BIAS card (line 12309):
Current trend text: `'Run your first analysis to start tracking here'`
Replace with: `'Your buy/sell ratio shows up after your first signal'`

---

## 3. TOOLTIP EXPLANATIONS — _dvGuide Entries

All entries follow the existing _dvGuide format:
```
'key': {
  title: 'Human-readable title',
  body: 'Beginner-friendly explanation (1-4 sentences)',
  example: 'Example with numbers (optional)'
}
```

### 3.1 Performance Stats metrics

#### perf-sharpe
```
'perf-sharpe': {
  title: 'Sharpe Ratio — Are Your Returns Worth the Risk?',
  body: 'The Sharpe ratio compares your returns to how bumpy the ride was. A ratio above 1.0 means you are earning more than the extra risk you took. Below 0 means you lost money. Think of it as a "smoothness score" — two traders can both make +10% but the one with smaller swings gets a higher Sharpe.',
  example: 'Sharpe 1.5 = good (returns are worth the risk). Sharpe 0.3 = low (you are taking risk without enough reward). Sharpe -0.8 = negative (your strategy is losing money after adjusting for risk).'
}
```

#### perf-winrate
```
'perf-winrate': {
  title: 'Win Rate — How Often Do You Win?',
  body: 'The percentage of your closed trades that ended as wins. A high win rate feels good but is not the full story — a trader with 40% win rate can be more profitable than one with 70% if their wins are much bigger than their losses. Win rate only matters in combination with your average reward:risk ratio.',
  example: '60% win rate with 1:1 R:R = profitable. 40% win rate with 1:2.5 R:R = also profitable. 70% win rate with 1:0.5 R:R = losing strategy (one loss wipes out two wins).'
}
```

#### perf-profit-factor
```
'perf-profit-factor': {
  title: 'Profit Factor — How Big Are Your Wins vs Losses?',
  body: 'Profit factor = total money won divided by total money lost. A profit factor of 2.0 means your wins are twice as big as your losses overall. Above 1.5 is excellent. Below 1.0 means you have lost more than you have won — your strategy is unprofitable regardless of win rate.',
  example: 'Total wins $15,000 · Total losses $5,000 → Profit factor 3.0. Total wins $8,000 · Total losses $12,000 → Profit factor 0.67 (losing strategy).'
}
```

#### perf-expectancy
```
'perf-expectancy': {
  title: 'Expectancy — How Much Do You Make Per Trade?',
  body: 'Expectancy is the average profit (or loss) per trade, measured in R-multiples. If you risk $100 per trade and your expectancy is +0.3R, you make roughly $30 per trade on average over many trades. Positive expectancy = your strategy works. Negative = you are slowly bleeding money. This is the most important number on this page.',
  example: 'Expectancy +0.35R with 100 trades per month = +35R/month. If 1R = $200, that is $7,000/month expected profit. Expectancy -0.15R = losing $15 per trade on average — stop trading and fix your strategy first.'
}
```

#### perf-stats
```
'perf-stats': {
  title: 'Performance Stats — Your Strategy Health Check',
  body: 'These four numbers together tell you if your trading strategy works. You want: Sharpe above 1.0, win rate above 40% (with good R:R), profit factor above 1.5, and positive expectancy. One bad number is not fatal — all four bad numbers means you need to change your approach.',
  example: 'A healthy strategy: Sharpe 1.4 · Win Rate 52% · Profit Factor 2.1 · Expectancy +0.4R. A struggling strategy: Sharpe -0.3 · Win Rate 35% · Profit Factor 0.8 · Expectancy -0.2R.'
}
```

### 3.2 Charts and Visuals

#### perf-pnl-curve
```
'perf-pnl-curve': {
  title: 'PnL / Equity Curve — Your Profit Over Time',
  body: 'This chart tracks your cumulative profit measured in R-multiples. One "R" equals whatever you risk per trade. A rising green line means you are profitable. The gold dashed line is your all-time high — whenever the green line dips below it, you are in drawdown. The red shaded areas highlight those dips.',
  example: 'If you risk $200 per trade and the chart shows +8.5R, you are up $1,700 total. If the green line has been flat for 10 trades, your strategy may have stopped working — investigate.'
}
```

#### perf-drawdown
```
'perf-drawdown': {
  title: 'Drawdown — How Deep Are Your Losing Streaks?',
  body: 'Drawdown measures the drop from your peak equity to the lowest point after it. It tells you how much pain your strategy can inflict. A 10% drawdown on a $10,000 account means you were down $1,000 at the worst point. Under 10% is normal. Over 25% is dangerous — most traders quit during deep drawdowns.',
  example: 'Peak equity $12,000 · Current equity $10,800 → 10% drawdown. If your strategy has a historic max drawdown of 30%, expect to lose up to 30% of your account at some point — size your positions accordingly.'
}
```

#### perf-heatmap
```
'perf-heatmap': {
  title: 'Monthly Returns Heatmap — Your Trading Calendar',
  body: 'A color-coded calendar showing how much you made or lost each month, in R-multiples. Green cells = profitable months. Red cells = losing months. A dot means no trades that month. Look for seasonal patterns — do you always lose in September? Do you always win in January? These patterns help you decide when to trade more aggressively and when to pull back.',
  example: 'If every December shows -5R or worse, consider taking December off or trading smaller. If March consistently shows +3R or better, that is your power month — lean in.'
}
```

### 3.3 Cards

#### perf-expectancy-card
```
'perf-expectancy-card': {
  title: 'Trade Expectancy — Your Mathematical Edge',
  body: 'Expectancy is calculated from your actual closed trades. It multiplies your win rate by your average win size, then subtracts your loss rate times your average loss size. The result is your expected profit per trade. A positive number means your strategy has a statistical edge — over many trades, you should come out ahead.',
  example: 'Win rate 45% · Avg win +2.1R · Avg loss -0.9R → Expectancy = (0.45 × 2.1) + (0.55 × -0.9) = +0.45R per trade. Even with more losses than wins, you are profitable because your wins are more than twice as big as your losses.'
}
```

#### perf-asset-breakdown
```
'perf-asset-breakdown': {
  title: 'Signals by Asset Class — Where Are You Trading?',
  body: 'This breakdown shows which types of assets your signals target. Stocks, crypto, forex, indices, and commodities behave differently. If 80% of your signals are in crypto, a crypto market crash will hit your entire account. Diversifying across 2-3 asset classes means one bad market does not wipe you out.',
  example: 'Good mix: 40% crypto, 30% stocks, 30% forex → if crypto crashes, only 40% of your trades are affected. Risky mix: 95% crypto, 5% other → a crypto bear market stops your trading completely.'
}
```

#### perf-targets
```
'perf-targets': {
  title: 'Your Targets — Personal Trading Benchmarks',
  body: 'These are goals you set for yourself in Settings → Performance. They are not predictions — they are standards you hold yourself to. If your actual numbers consistently miss these targets, either your targets are too aggressive or your strategy needs improvement. Adjust them as you learn what is realistic.',
  example: 'Target win rate 55% · Actual 48% → you are 7% below target. Either work on trade selection to improve win rate, or lower your target to something realistic based on your strategy type (trend followers often have lower win rates with higher R:R).'
}
```

#### perf-recent-activity
```
'perf-recent-activity': {
  title: 'Recent Signal Activity — Your Trade Log',
  body: 'A chronological list of your most recent signals. Each row shows the direction (BUY/SELL/HOLD), ticker, timeframe, entry price, confidence, and whether it expired. Click Log Result to record whether the trade won or lost — this data feeds all the performance stats above. Expired signals are dimmed but can still be logged if the trade completed.',
  example: 'Signal: BUY BTCUSDT at $67,200 · 82% confidence · 4H timeframe. If the trade hit your stop loss at $65,800, log it as a LOSS. If it hit TP1 at $71,000, log it as a WIN.'
}
```

#### perf-calibration
```
'perf-calibration': {
  title: 'Confidence Calibration — Do Your Scores Mean What They Say?',
  body: 'Calibration checks whether "82% confidence" signals actually win 82% of the time. If your 80% signals only win 55% of the time, they are overconfident — calibration adjusts the score down. This uses isotonic regression, a statistical method that maps raw scores to real probabilities based on your actual trade outcomes.',
  example: 'Before calibration: 80% raw confidence → 55% actual win rate (overconfident by 25pp). After calibration: same signal shows 55% calibrated confidence. This honest number helps you decide which signals to take and which to skip.'
}
```

#### perf-daily-cap
```
'perf-daily-cap': {
  title: 'Daily Trades Cap — Stop Overtrading',
  body: 'A hard limit on how many signals you can act on per day. Overtrading is one of the biggest account killers — taking every signal you see leads to low-quality trades, revenge trading, and exhaustion. Set a cap that matches your attention span and risk tolerance. When you hit the cap, stop. The market will be there tomorrow.',
  example: 'Cap set to 3 trades per day. You have taken 2 so far today → one more trade available. Cap set to 5 but you are a part-time trader → consider lowering to 3 so you can give each trade proper attention.'
}
```

---

## 4. ATTACHMENT SUMMARY

Where to add `data-guide` attributes so the tooltips fire:

| Metric / Element | `data-guide` value | Location |
|---|---|---|
| Performance Stats card title | `perf-stats` | The `perf-card-title` span in _statsCard |
| Sharpe Ratio stat box | `perf-sharpe` | The div containing "SHARPE RATIO" label |
| Win Rate stat box | `perf-winrate` | The div containing "WIN RATE" label |
| Profit Factor stat box | `perf-profit-factor` | The div containing "PROFIT FACTOR" label |
| Expectancy stat box (in stats) | `perf-expectancy` | The div containing "EXPECTANCY" label |
| PnL / Equity Curve card title | `perf-pnl-curve` | The `perf-card-title` span |
| Drawdown card title | `perf-drawdown` | The `perf-card-title` span |
| Monthly Heatmap card title | `perf-heatmap` | The `perf-card-title` span |
| Trade Expectancy card title | `perf-expectancy-card` | The `perf-card-title` span |
| Signals by Asset Class card title | `perf-asset-breakdown` | The `perf-card-title` span |
| Your Targets card title | `perf-targets` | The `perf-card-title` span |
| Recent Signal Activity card title | `perf-recent-activity` | The `perf-card-title` span |
| Confidence Calibration card title | `perf-calibration` | The `perf-card-title` span |
| Daily Trades Cap stat box (in targets) | `perf-daily-cap` | The div containing "DAILY TRADES CAP" label |

---

## 5. IMPLEMENTATION NOTES

- The `data-guide` attribute should be added to the HTML element that wraps the metric label/card title. Example: `<span class="perf-card-title" data-guide="perf-stats">Performance Stats</span>`
- All empty state replacements should use the same font, color, and sizing conventions as the existing page (font-family: var(--mono) for labels, sans-serif for body text; color: rgba(237,232,216,.3–.5) for muted text)
- Section description divs should use the existing border-top: 1px solid var(--bd) separator convention to visually attach to the card body
- The _dvGuide entries must be placed inside the `window._dvGuide = { ... }` block (starting line 21285), grouped together under a `// ── PERFORMANCE TAB ──` comment heading
- Do NOT change any existing CSS classes or layout grid values
- The dvGuideInit() mouseover system already works — just add `data-guide` attributes and _dvGuide entries
