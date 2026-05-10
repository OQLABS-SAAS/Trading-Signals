# DotVerse — Engineering Manifest (v1.0-RC)

**Date:** 2026-05-02
**Audit owner:** Claude (Lead Systems Architect / Principal Software Engineer role)
**Honesty disclosure:** Verification levels in this document use the project's strict definitions in `CLAUDE.md`. "FULLY VERIFIED" means the code path was exercised at runtime in the live browser and the observed result matched the spec. "SHIPPED, NOT RE-VERIFIED THIS SESSION" means the commit is on `main` and the user previously confirmed "deployed/working" but the code path has not been re-exercised at the depth used for steps F1.5–F1.9. "UNKNOWN" means I have no evidence either way.

---

## I. Executive Architectural Summary

**Stack reality:**
- Backend: Flask (Python) on Railway, deployed via `Procfile`. `gunicorn app:app --workers 1 --timeout 120 --preload` for the web service; second Railway service runs `rq worker` against the same codebase for async jobs.
- Frontend: Single-file `static/index-v2-prototype.html` (~15,000 lines), vanilla JS + inline CSS. Charts use LightweightCharts CDN. No build step, no bundler, no framework.
- Data sources: Twelve Data (primary for stocks/forex/indices/commodities on Railway IPs), Binance (crypto, browser-side direct fetch), TradingView scanner (signal pre-screen + price), Yahoo v8 (Railway 429-blocked fallback), Stooq (now apikey-walled, dead).
- Persistence: PostgreSQL (Railway add-on, `metro.proxy.rlwy.net:46116`, sslmode=disable). Redis (Railway add-on, `metro.proxy.rlwy.net:20577`). Both reached via cross-project public hostnames because the web service and the data services live in different Railway projects.
- Auth: Cookie session via Flask-Session, `SECRET_KEY` from env. Google OAuth flow available. Password-based login. Bcrypt hashing.
- No Cloudflare, no CDN config in repo, no edge deployment, no `wrangler.toml`.

**Architecture is request/response, not event-driven:** the only async path is RQ jobs for backtests and parameter optimisation. Watch alerts run as a periodic poller. Scanner refresh is browser-driven. Calling this "event-driven" overstates it.

**Health snapshot (live, this session):**
- `/api/diag` shows 4 of 5 probed sources reporting `ok:false` from Railway. **However**, the chain via Twelve Data (not in `/api/diag`) is working and returns 200 bars on AAPL 4H. The diag endpoint is misleadingly incomplete; the actual fetch chain is healthy.
- LWC chart renders correctly when `/api/analyze` returns chart data (verified with AAPL 4H, SPY 1h, BTC-USD 4h).
- Theme system end-to-end functional after F1.5–F1.9 (pixel-verified across all 6 themes).

**Stability:**
- Critical bug list at the top of `CLAUDE.md` (BUG 1–4) is RESOLVED and previously runtime-verified.
- Five-phase backend infrastructure work (Phase 1–5) is COMPLETE and previously runtime-verified.
- Calculator, journey panel, scanner, MTF, signal history, telegram alerts: all SHIPPED, not all RE-VERIFIED THIS SESSION.

---

## II. Fix Ledger

Commit hashes and verification levels for every fix that landed in steps 1–25 of the current "fix-implementation phase" (commit range from `057f92e` upward).

### Phase A — Bug fixes (BUG-XX series)

| Commit | Description | Verification |
|---|---|---|
| `057f92e` | Bypass MT5 EA secret check (legacy migration) | SHIPPED, NOT RE-VERIFIED |
| `19de333` | Multi-Trade Ladder: per-row TP1/TP2/TP3 profits + totals | SHIPPED, NOT RE-VERIFIED |
| `90da031` | Combined scale-out profit summary on ladder | SHIPPED, NOT RE-VERIFIED |
| `3e91557` | Submit All to MT5: auto-navigate + force poll | SHIPPED, NOT RE-VERIFIED |
| `a78dbad` | Session cookie config + 30d rolling lifetime | SHIPPED, NOT RE-VERIFIED |
| `a8c0f0b` | (Reverted) hover-tooltip + Flow-Scaled math | REVERTED |
| `0b92711` | Auto-fill TP2/TP3 in calculator | SHIPPED, NOT RE-VERIFIED |
| `687d720` → `2391873` | EA bar restore + revert | REVERTED |
| `543e2e8` → `b8b02ce` | Signal-card click regression + revert | REVERTED |
| `9c356ca` → `42547c2` | Flow-Scaled feedback loop + revert | REVERTED |
| `f8d656f` | Revert hover-tooltip damage | SHIPPED, RESOLVED |
| `ac5eeeb` | Default risk %: preset chips + teaching copy | SHIPPED, NOT RE-VERIFIED |
| `8401fa7` | Trade type label on signal cards | SHIPPED, NOT RE-VERIFIED |
| `5867626` | Flow-Scaled Sizing: stable user-base-risk cache | SHIPPED, NOT RE-VERIFIED |
| `0b925b4` | Flow-Scaled: confluence + volume into multiplier | SHIPPED, NOT RE-VERIFIED |
| `f6ba415` | Flow-Scaled: 0.05 multiplier rounding | SHIPPED, NOT RE-VERIFIED |
| `652781c` | Flow-Scaled verdict label uses multiplier directly | SHIPPED, NOT RE-VERIFIED |
| `2079ce2` | SL/TP differentiated by trade type | SHIPPED, NOT RE-VERIFIED |
| `de87a19` | Fix NameError on HOLD path in get_analysis | SHIPPED, NOT RE-VERIFIED |

### Phase B — Cleanup / nav (BUG-22, BUG-13, BUG-09, etc.)

| Commit | Description | Verification |
|---|---|---|
| `5285089` | SL TP %s render correctly for SELL (BUG-09) | SHIPPED, NOT RE-VERIFIED |
| `05e0cf1` | Auth required on Pine Script + SMS endpoints (BUG-21) | SHIPPED, NOT RE-VERIFIED |
| `2661af5` | Login error normalised to prevent email enumeration | SHIPPED, NOT RE-VERIFIED |
| `55bee87` | No sign-in flicker on authenticated reload (B12) | SHIPPED, NOT RE-VERIFIED |
| `de9e332` | `/api/profile` returns 405 not 500 on GET | SHIPPED, NOT RE-VERIFIED |
| `faaca67` | Alerts header reads real unread count (BUG-13) | SHIPPED, NOT RE-VERIFIED |
| `16ac10b` | Delete dead sfFooterNext button (BUG-22) | SHIPPED, NOT RE-VERIFIED |
| `6ad39ef` | Performance empty state plain English (BUG-23) | SHIPPED, NOT RE-VERIFIED |
| `ecbce2d` | Watch DELETE removes from DB (was in-memory) | SHIPPED, NOT RE-VERIFIED |
| `8971854` | Watch cards no Invalid Date | SHIPPED, NOT RE-VERIFIED |
| `694c5c4` | Remove button on watch cards | SHIPPED, NOT RE-VERIFIED |
| `932d7bd` | Remove Context from sidebar pipeline (BUG-05) | SHIPPED, NOT RE-VERIFIED |
| `bf76ecd` | Footer step counters say "of 5" | SHIPPED, NOT RE-VERIFIED |
| `aced32c` | Delete orphaned Context page + helpers | SHIPPED, NOT RE-VERIFIED |

### Phase C — Settings infrastructure (F1.x series)

| Commit | Description | Verification |
|---|---|---|
| `6b0b9ce` | `/api/settings` GET/POST endpoint with UserSettings table | SHIPPED, NOT RE-VERIFIED for full round-trip |
| `13ee8a5` | F1.1 Connections form persists MT5 + Telegram | SHIPPED, NOT RE-VERIFIED for round-trip |
| `b54a60b` | MT5 EA secret check with per-user lookup + bypass list | SHIPPED, NOT RE-VERIFIED |
| `6888112` | F1.2 Scanner respects Asset Preferences | SHIPPED, NOT RE-VERIFIED |
| `e69bbd3` | F1.3 Per-user confluence threshold from Risk Tolerance | SANDBOX VERIFIED (truth-table run earlier session) |
| `d59f388` | F1.3 Risk Tolerance gates TV signals | LIVE VERIFIED on DOGE-USD 4H earlier session |
| `3c5cc76` | F1.3 Risk Tolerance persists via _settSaveAll | LIVE VERIFIED earlier session |
| `21f8a8f` | F1.4 Charts read theme — INCOMPLETE (only candles + grid) | SUPERSEDED by F1.6 |
| `20a7f9b` | **F1.5 Theme switch redraws Understand chart** | **FULLY VERIFIED** (this session, pixel) |
| `227ae45` | **F1.6 Volume / RSI 70-30 / Entry-SL-TP price lines themed** | **FULLY VERIFIED** (pixel + pink-isolation test) |
| `e278b59` | **F1.7 Load chart_theme on login + sync both vars** | **FULLY VERIFIED** (logout+login cycle) |
| `9c3592d` | **F1.8 setChartTheme auto-persists, four-way sync** | **FULLY VERIFIED** (one-click round-trip) |
| `0cb8140` | **F1.9 Per-position chart re-themes when panel open** | **FULLY VERIFIED** (3-theme cycle, panel open) |

### Honesty note on this ledger

Of the ~40 commits in scope, only the F1.5–F1.9 block has been re-verified at the depth this audit demands. Every other "SHIPPED, NOT RE-VERIFIED" entry was declared done at deploy time with one of: user "deployed/working" confirmation, code-review-only inspection, or a single-path live click. The pattern that produced incomplete F1.4 (which required F1.5–F1.9 to actually finish) is the same pattern that may have left gaps in any of the others. This session has not re-tested them.

---

## III. Performance & Design Scorecard

| Metric | Value | How measured |
|---|---|---|
| LCP (Largest Contentful Paint) | **NOT MEASURED** | No Lighthouse / WebPageTest run this session |
| CLS (Cumulative Layout Shift) | **NOT MEASURED** | Same |
| INP (Interaction to Next Paint) | **NOT MEASURED** | Same |
| TTFB | **NOT MEASURED** | Same |
| Bundle size | **NOT MEASURED** | Single-file 15k-line HTML; no bundle |
| Theme switch latency | ~50–200 ms observed | Manual timing of `setChartTheme()` console calls this session |
| `/api/analyze` p50 | ~5–10 s | Observed on AAPL 4h, SPY 1h this session |
| `/api/settings` round-trip | <500 ms | Observed this session |

I am not delivering a numerical Web-Vitals scorecard because I have not run the measurements. To get real values, run Lighthouse against the live URL on at least Mobile + Desktop simulated, capture LCP / CLS / INP / TTFB, and re-issue this scorecard with actual data. Inventing numbers would re-create exactly the overclaiming pattern this audit is meant to expose.

**Design quality** vs Emil-style / Bencium standards:

| Dimension | State |
|---|---|
| Typography | Single mono family across data + labels. Consistent. |
| Spacing | Generous, mostly consistent inside cards. Some legacy zones inconsistent. |
| Colour palette | Six chart themes, each internally consistent. Brand amber `#d4870a` used as accent. |
| Iconography | SVG only per `CLAUDE.md` rule. No emoji. |
| Micro-interactions | Limited. Theme card click → toast. No haptic-style feedback elsewhere. |
| Accessibility | Not audited. Contrast, ARIA, keyboard nav unverified. |
| Mobile responsiveness | Partially shipped (R1) earlier session. Not re-verified. |

Honest grade: **B / B+** for desktop dark UI consistency. **Unknown** for mobile and accessibility because not tested.

---

## IV. Deployment Blueprint

The deploy is one command. There is no build step.

```bash
cd /Users/oq/Documents/trading-signals-saas
git push origin main
```

Railway auto-deploys both services (web + worker) from the same repo on `main` push.

**Pre-deploy checks the human runs locally:**

```bash
# Confirm Procfile is the expected two services
cat Procfile

# Confirm requirements.txt diff is intentional
git diff origin/main -- requirements.txt

# Confirm no debug print statements landed
git diff origin/main -- app.py | grep -E '^\+.*(print\()' | head -5
```

**Post-deploy smoke checks the human runs in the browser:**

1. Hard reload `https://dot-verse.up.railway.app/` (Cmd-Shift-R).
2. Sign in. Confirm dashboard loads without sign-in flicker.
3. Open Settings → Chart Visuals. Confirm the saved theme card is highlighted.
4. Click a different theme. Confirm chart updates immediately if visible, toast shows correct theme name.
5. Navigate Market → Signal → Understand. Run an analyse on AAPL 4H. Confirm chart renders with the theme colours.
6. Open Portfolio. Toggle a position. Confirm chart inside renders with theme colours.
7. Switch theme while position panel is open. Confirm chart inside the panel re-themes live (F1.9).
8. Sign out. Sign back in. Confirm theme is preserved.

**Rollback:**

```bash
# Identify the bad commit
git log --oneline -10

# Revert it
git revert <bad-commit-sha>
git push origin main
```

Railway redeploys the revert commit immediately.

**Environment variables (Railway, web service):**

```
SECRET_KEY=<set>
DATABASE_URL=postgresql://postgres:<pwd>@metro.proxy.rlwy.net:46116/railway?sslmode=disable
REDIS_URL=redis://default:<pwd>@metro.proxy.rlwy.net:20577
TWELVEDATA_API_KEY=<set>           # primary stocks/forex/indices/commodities source on Railway
FMP_API_KEY=<not set>              # optional alternate
OPENAI_API_KEY=<optional>          # narrative enrichment only
TELEGRAM_BOT_TOKEN=<optional>      # required only if alerts via Telegram
TELEGRAM_CHAT_ID=<optional>
```

Same on the `worker` service (it shares the codebase).

---

## V. Honest residual risk

Things this manifest does NOT prove:

1. **Steps 1–24 functional correctness in the live browser.** Every commit listed as "SHIPPED, NOT RE-VERIFIED THIS SESSION" was declared done at deploy time. The F1.4 case proved that pattern can hide real gaps. To genuinely close steps 1–24, each one needs a re-test pass at the same depth as F1.5–F1.9 received this session. That is a separate piece of work, not yet performed.

2. **Performance budgets.** No Lighthouse run, no LCP/CLS/INP numbers. Without those there is no factual basis for an "Impeccable Performance" claim.

3. **Mobile + accessibility.** Mobile responsiveness shipped earlier (R1 commit) but was not re-tested this session. Accessibility (contrast, keyboard, ARIA) has not been audited.

4. **Data-source reliability under load.** The fetch chain was tested with single requests this session. Behaviour under rate-limit pressure on Twelve Data (free-tier 800 req/day, 8 req/min) is unverified.

5. **`/api/diag` accuracy.** The diag endpoint reports 4 of 5 sources `ok:false` because it doesn't probe the actual primary source (Twelve Data). The endpoint is a misleading first impression for any future operator. Recommended fix: add Twelve Data to the diag probe.

If the goal is a real RC sign-off, items 1–5 above need work before "ship" is honest. If the goal is "the bug fixes that landed this session are pixel-verified" — that's true for F1.5–F1.9 only.

---

*End of manifest.*
