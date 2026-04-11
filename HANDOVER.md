# DotVerse Trading Signals — Session Handover

**Last updated:** 2026-04-11
**Repo:** https://github.com/OQLABS-SAAS/Trading-Signals
**Deployed:** https://dot-verse.up.railway.app/
**Last commit:** `4cfc40c fix(rsi-div): history-mode Pine export + chart toggle fallback`

## Quick start for a new Claude session

Before doing anything else, run:

```
git pull
git log --oneline -6
```

Then read these files to get oriented:
- `app.py` — `detect_rsi_divergence()` around line 353 (pivot-based engine, emits `all` list)
- `static/index.html` — search for `PINE_DIVERGENCE` (line ~6538), `copyDivergence` (line ~9104), `divHistoryMode` (line ~3654), `toggleDivHistory` (line ~9420)
- `static/dotverse_rsi_divergence.pine` — standalone Pine indicator

## Recent work (commits 6839f45 → 4cfc40c)

### 1. RSI Divergence History Mode (6839f45)
Added a toggleable "History Mode" to the RSI divergence indicator so it shows **every** detected divergence in the lookback window (Binary Destroyer style), not just the most recent one.

- **Backend** (`app.py`): `detect_rsi_divergence()` now walks every consecutive pivot pair and returns an `all` list ordered oldest → newest. The most recent is still surfaced at the top level for backward compat.
- **Frontend** (`static/index.html`):
  - Globals: `chartDivergence` (most recent), `chartDivergenceAll` (full list), `divHistoryMode` (toggle state)
  - Price chart drawing and RSI sub-chart plugin both support dual-mode: history uses an alpha fade ramp (`0.28 + t * 0.57`) so older lines dim and newest is brightest.
  - Toggle button "⟿ Div History" on the signals page, wired to `toggleDivHistory()` which flips state and re-renders charts.
- **Pine script** (`static/dotverse_rsi_divergence.pine` + inline `PINE_DIVERGENCE` template): `showHistory` input default TRUE. When ON, each divergence is drawn unconditionally via `line.new()` with `lastHistReg{Bull,Bear}Idx` dedup trackers. When OFF, falls back to the reusable slot pattern.

### 2. Two bug fixes (4cfc40c)
- **Div History toggle showing nothing on the chart**: Added fallback in both the price chart drawing and RSI sub-chart plugin — when `chartDivergenceAll` is empty, history mode still shows the classic single divergence via `chartDivergence`. So the chart never goes blank while waiting for backend data.
- **Backtest tab Pine script not matching TradingView view**: `copyDivergence()` at line 9104 was a separate generator emitting only `plotshape` markers with no line drawing. Rewrote it to reuse the full `PINE_DIVERGENCE` template literal (same pivot-based multi-line engine as in-app chart and the standalone `.pine`), with a ticker/timeframe header prepended. Default History Mode ON.

## Known open items / things to verify after deploy

1. **Verify backend is deployed with 6839f45**: The `rsi_divergence.all` field must be present in `/analyze` responses for the signals page history toggle to show multiple lines. If it's missing, redeploy Railway.
2. **Test "⟿ Div History" toggle** on a few assets with multiple historical divergences.
3. **Test "Copy RSI Div"** button in backtest tab — paste into TradingView Pine Editor and confirm the framed Binary Destroyer-style view with lines across history.
4. Untracked file `design_preview.html` is not committed; decide whether to add or ignore.

## Architecture notes

- **Two Pine generators exist** in `static/index.html`:
  1. `PINE_DIVERGENCE` const template literal at line ~6538 — the canonical, full-featured indicator. Displayed in the Pine code panel via `codeEl.textContent = PINE_DIVERGENCE`.
  2. `copyDivergence()` at line ~9104 — the per-backtest copy button. As of 4cfc40c this now delegates to `PINE_DIVERGENCE` with a ticker/timeframe header.
- Keep these in sync. If you change divergence detection logic in one, update the other.
- `PINE_DIVERGENCE` is a top-level `const` at module scope in the inline `<script>` so it's accessible from any function defined in that script block.

## Key file locations

| What | Path | Line |
|---|---|---|
| Python divergence engine | `app.py` | ~353 |
| `chartDivergence` globals | `static/index.html` | ~3649 |
| Price chart div drawing | `static/index.html` | ~3900 |
| RSI sub-chart plugin | `static/index.html` | ~4300 |
| `PINE_DIVERGENCE` template | `static/index.html` | ~6538 |
| `getPineDivergence()` | `static/index.html` | ~7210 |
| `copyDivergence()` | `static/index.html` | ~9104 |
| `toggleDivHistory()` | `static/index.html` | ~9420 |
| Standalone Pine file | `static/dotverse_rsi_divergence.pine` | — |
