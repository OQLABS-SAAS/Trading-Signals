# DotVerse v2 — Complete Bug Report
**File audited:** `static/index-v2-prototype.html` (~13,869 lines)  
**Audit date:** 2026-04-28  
**Method:** Full static code audit — every finding traced to exact line numbers. No guessing.

---

## CRITICAL — Breaks core functionality

---

### BUG-01 · Auto-refresh on SIGNAL page is completely broken
**Symptom:** Clicking OFF / 15s / 30s / 1m / 5m / 15m buttons on the SIGNAL page does nothing. No timer starts, no refresh happens.

**Root cause:** There are two `arSet` functions defined in the file:
- `function arSet(secs, btn)` at **line 4486** — handles the SIGNAL page's `ar-btn` buttons. Signature: `(seconds, buttonElement)`.
- `function arSet(btn)` at **line 7153** — handles the SCANNER's `ar-pill` buttons. Signature: `(buttonElement only)`.

JavaScript last-definition wins. `arSet` at line 7153 permanently overwrites the one at line 4486.

When the SIGNAL page `ar-btn` buttons fire (e.g. `onclick="arSet(15, this)"`), the v2 function receives `btn=15` (a number). It then calls `btn.classList.add('active')` → `15.classList` → **TypeError crash**. Auto-refresh does nothing and the countdown never starts.

**Lines:**
- Duplicate definitions: 4486 and 7154
- SIGNAL page callers (broken): 6996–7001
- SCANNER callers (working): 7086–7091

**Fix:** Merge into one function that handles both call signatures, or rename them and update all callers.

---

### BUG-02 · Login button bypasses authentication entirely
**Symptom:** Clicking "Sign In to DotVerse" logs the user in without calling the backend. Any email/password (including blank fields) opens the full dashboard.

**Root cause:** The Sign In button at **line 4561** calls `goDash()` directly. `goDash()` (line 4516) just shows the dashboard view — no call to `/api/login`, no session cookie, no token. The backend auth system exists and works, but the frontend never uses it.

**Lines:**
- Sign In button: 4561
- `goDash()`: 4516

**Fix:** Replace `onclick="goDash()"` with a function that calls `POST /api/login`, checks the response, and only calls `goDash()` on success. Handle wrong password with an error message.

---

### BUG-03 · Signal cards from API missing tp2 / tp3 — SIZE tab always shows empty TP2/TP3
**Symptom:** After clicking Analyse on any signal card, the SIZE tab shows TP1 filled but TP2 and TP3 are always blank.

**Root cause:** The mapping object built in `_sfFetchSignals()` (lines 6721–6733) only maps `tp: r.tp1`. It does not map `tp2` or `tp3`. When `loadSignalContext(o)` runs (line 7372), `_calcPrefill` is set to `{entry, sl, tp, sym}` — no tp2/tp3. The SIZE tab input fields for TP2 (line 10804) and TP3 (line 10810) have no `value=` attribute and no post-render code sets them.

**Lines:**
- Mapped object (missing tp2/tp3): 6721–6733
- loadSignalContext _calcPrefill: 7374
- SIZE tab TP2 input (no value): 10804
- SIZE tab TP3 input (no value): 10810

**Fix:** Add `tp2: r.tp2 || '--', tp3: r.tp3 || '--'` to the mapped object in `_sfFetchSignals`. Add `tp2: o.tp2, tp3: o.tp3` to `_calcPrefill` in `loadSignalContext`. Add `value="${String(sig.tp2||pf.tp2||'').replace(/,/g,'')}"` and `value="${String(sig.tp3||pf.tp3||'').replace(/,/g,'')}"` to the TP2 and TP3 input fields in `showSize`.

---

### BUG-04 · UNDERSTAND tab "← SIGNAL" back button goes nowhere (refreshes same page)
**Symptom:** On the UNDERSTAND tab, the back button is labelled "← SIGNAL" but clicking it stays on UNDERSTAND — it does not navigate to the SIGNAL tab.

**Root cause:** Line 10294: `onclick="setNav('understand');showUnderstand();"` — both the `setNav` call and the function call point to `understand`, not `signals`.

**Line:** 10294

**Fix:** Change to `onclick="setNav('signals');showSignalFeed();"`.

---

### BUG-05 · CONTEXT page is orphaned from the 5-step flow
**Symptom:** The CONTEXT tab is accessible from the sidebar but has no slot in the top navigation pill bar (MKT › SIG › UND › SZE › ACT). Clicking "Find Signals →" from CONTEXT goes back to SIGNAL instead of advancing the user. The flow progress dots don't update when on CONTEXT because `setNav` (line 4398) only knows `['market','signals','understand','size','act']` — 'context' is not in the array.

**Root cause (three issues):**
1. `setNav` steps array at line 4398 does not include `'context'`.
2. The CONTEXT page footer "Find SCALP Signals →" button (line 9665) calls `setNav('signals');showSignalFeed()` — same as the BACK button. Both buttons do the same thing.
3. The top pill bar (lines 4130–4138) has no `context` pill, so the user has no visual breadcrumb when on that page.

**Lines:** 4398, 9664, 9665

**Fix:**
- Add `'context'` to the steps array at line 4398 between `'signals'` and `'understand'`.
- Add a `CTX` pill to the top breadcrumb bar.
- Change the "Find Signals →" next button to advance to `understand` (step 4), not go back to `signals`.

---

### BUG-06 · CONTEXT page footer step label is wrong and shared with UNDERSTAND
**Symptom:** The CONTEXT page footer shows "Step 3 of 5 · UNDERSTAND" (line 9660). The UNDERSTAND page also shows "Step 3 of 5 · UNDERSTAND" (line 10290). Two different pages show the same step number and the same label.

**Root cause:** The SIGNAL tab shows "Step 2 of **6**" (line 7066) while all other pages count "of 5". Step numbering is inconsistent across all tabs.

**Lines:** 7066 ("of 6"), 9660, 10290

**Fix:** Decide on the canonical step count (5 or 6, depending on whether CONTEXT is a step). Update all `flow-footer-step` labels to be unique and consistent:
- Market = Step 1 of 6
- Signal = Step 2 of 6
- Context = Step 3 of 6
- Understand = Step 4 of 6
- Size = Step 5 of 6
- Act = Step 6 of 6

---

## HIGH — Broken features users will hit immediately

---

### BUG-07 · Strategy mode default is inconsistent — 'all' vs 'scalp' conflict
**Symptom:** After a hard refresh, the mode pill on the SIGNAL page shows "ALL" active, but the CONTEXT page highlights "Scalp" as the active card. The two pages disagree.

**Root cause:**
- Line 9470: `window._stratMode = localStorage.getItem('dv_strat_mode') || 'all'` — default is `'all'`.
- Line 4518 (`_initStratMode`): `const saved = window._stratMode || 'scalp'` — fallback is `'scalp'`.
- Line 9562 (`showContext`): `const curMode = window._stratMode || 'scalp'` — fallback is `'scalp'`.

If localStorage has no saved mode, `window._stratMode` is set to `'all'` at line 9470. But `showContext` reads `window._stratMode || 'scalp'` which evaluates to `'all'` (not `'scalp'`), so the context card highlights ALL. However `_initStratMode` tries to find `document.getElementById('sm-all')` at startup — but those buttons only exist after `_sfRender()` runs, so the active class never gets set at startup.

**Lines:** 9470, 4518, 9562

**Fix:** Pick one default ('all' is correct). Remove the `|| 'scalp'` fallbacks at lines 4518 and 9562. Change both to `|| 'all'`. Remove `_initStratMode()` call from `goDash()` and instead call it inside `showSignalFeed()` after the DOM exists.

---

### BUG-08 · Market page scan uses 10-second timeout and 2.5-second minimum wait
**Symptom:** Every time the Market page loads, the user waits a mandatory 2,500ms even if the API responds in 200ms. If the API is slow, the page hangs for up to 10,000ms before showing fallback data.

**Root cause:** Line 8071: `const minWait = new Promise(r => setTimeout(r, 2500))`. Line 8076: timeout is `10000`. The SIGNAL page uses `800ms` min wait and `5000ms` timeout (lines 6709, 6708). The Market page is 3× slower by design.

**Lines:** 8071 (2500ms minWait), 8076 (10000ms timeout)

**Fix:** Change `2500` to `800` and `10000` to `5000` to match the SIGNAL page.

---

### BUG-09 · SIZE tab shows "+-X%" for SELL signals
**Symptom:** On a SELL signal, the SIZE tab % price move displays as `+-1.23%` instead of `-1.23%`.

**Root cause:** Line 11288: `_s('szTP'+n+'Pct', assetType==='forex' ? t.tpPips.toFixed(1)+' pips' : '+'+t.pct+'%')`. The `calcTP` function computes `pct = ((tp-entry)/entry*100).toFixed(2)`. For SELL trades, `tp < entry`, so `pct` is a negative string like `"-1.23"`. Prepending `'+'` produces `"+-1.23%"`.

**Line:** 11288

**Fix:** Change to `(parseFloat(t.pct) >= 0 ? '+' : '') + t.pct + '%'`. Same issue applies to the `'+'+t.acctNet` and `'+'+t.acctGross` at line 11290 — fix those the same way.

---

### BUG-10 · Context page IPO listings are hardcoded mock data
**Symptom:** The "Hot Right Now · IPO & New Listings" section on the CONTEXT page always shows the same four tickers (RDZN, ALAB, LPSN, FROG) regardless of the real market date.

**Root cause:** Lines 9565–9569 define a hardcoded `ipos` array. The comment at line 9564 says "prototype: mock; production: fetch from /api/new-listings" — the production endpoint does not exist.

**Lines:** 9564–9569

**Fix:** Either remove the IPO section until the `/api/new-listings` endpoint exists, or replace it with a live data feed. Do not ship mock data as if it were live.

---

### BUG-11 · Context page session scores are hardcoded UTC-hour estimates, not real session data
**Symptom:** The session quality scores (GO / CAUTION / WAIT) on the CONTEXT page are computed from UTC hour ranges hardcoded in the function. They do not account for bank holidays, half-days, or actual liquidity.

**Root cause:** Lines 9502–9516 compute `sessScore` from `new Date().getUTCHours()` buckets. This is a prototype approximation.

**Lines:** 9502–9516

**Note for developer:** This is acceptable for v1 if labelled as approximate. If presenting as real data, replace with a market calendar API or clearly label it "estimated based on session hours."

---

### BUG-12 · Portfolio tab uses localStorage, not the PostgreSQL backend
**Symptom:** Positions added in the Portfolio tab are stored in `localStorage` (key `dv_pf_pos`) via `_pfSave()`. The Railway PostgreSQL database has a `positions` table and `/api/positions` endpoints that were built and verified, but the Portfolio tab frontend never calls them.

**Root cause:** `pfAddPosition()` at line 8538 calls `_pfLoad()` / `_pfSave()` (lines 8233–8234) which read/write `localStorage`. No `dvFetch('/api/positions', ...)` call anywhere in `showPortfolio` or `pfAddPosition`.

**Lines:** 8233–8234, 8538–8564

**Fix:** Replace `_pfLoad()` with `GET /api/positions`, replace `_pfSave` / `pfAddPosition` with `POST /api/positions`, and `pfDelete` with `DELETE /api/positions/:id`. VaR should call `GET /api/var` instead of the local `_pfComputeVar` approximation (which uses a hardcoded 1.5% std at line 8239).

---

### BUG-13 · Alerts tab shows hardcoded mock alerts — no real alert system wired
**Symptom:** The ALERTS page always shows the same six hardcoded alerts (GBP/JPY, BTC/USD, NVDA, AMZN, AAPL, SPX500) regardless of the user's actual positions or signal history.

**Root cause:** `showAlerts()` at line 9296 defines a hardcoded `alerts` array. No API call.

**Lines:** 9296–9310

**Fix:** Fetch from a real alerts endpoint, or clearly mark this as "coming soon" in the UI.

---

## MEDIUM — UX breaks and confusing behaviour

---

### BUG-14 · Sign In page has a missing closing quote causing malformed HTML
**Symptom:** The auth panel may render incorrectly in strict browsers.

**Root cause:** Line 4551: `'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:5px;"` — the closing `>` of the `div` tag is missing. The `style` attribute is opened with `"` but the tag itself is not closed before the next `'` string concat.

**Line:** 4551

**Fix:** Add `>` after the closing `"` of the style attribute: `...;margin-bottom:5px;">'+`.

---

### BUG-15 · "← SIGNAL" label on UNDERSTAND back button calls showUnderstand not showSignalFeed
**Symptom:** (Also reported as BUG-04.) For completeness: the SIZE tab back button (line 11023) correctly calls `setNav('understand');showUnderstand()` with the label "← UNDERSTAND". That one is correct. Only line 10294 is wrong.

---

### BUG-16 · setStratMode default inconsistency causes wrong mode card highlighted on first visit
**Symptom:** First-time user opens the app. Context page shows "Scalp" mode card as highlighted. Signal page shows "ALL" pill as active. These disagree.

**Root cause:** Covered in BUG-07 above. Worth a separate fix entry because the user experience confusion here is significant for new users.

---

### BUG-17 · SIGNAL tab footer "Check Context → UNDERSTAND" button label is wrong
**Symptom:** The button at line 7070 is labelled "Check Context → UNDERSTAND" but clicking it calls `setNav('understand');showUnderstand()` — it skips context entirely.

**Root cause:** Either the label is wrong (should say "→ UNDERSTAND") or the onclick is wrong (should go to context). The comment in `loadSignalContext` says "Auto-navigate to CONTEXT pre-trade gate" but the function goes to UNDERSTAND.

**Line:** 7070

**Fix:** If the intent is to go to Context first: change onclick to `setNav('context');showContext()`. If the intent is to go directly to Understand: change the button label to "Analyse Signal → UNDERSTAND".

---

### BUG-18 · _initStratMode called before strat pill buttons exist in the DOM
**Symptom:** On app load, the active mode pill is never highlighted until the user navigates to the SIGNAL tab for the first time.

**Root cause:** `goDash()` (line 4516) calls `_initStratMode()` which tries to find `document.getElementById('sm-all')`. But the strat-pill buttons (`id="sm-all"`, `id="sm-scalp"` etc.) are only created inside `_sfRender()`, which runs when the SIGNAL tab is first opened. At startup they don't exist yet. `getElementById` returns null, the `if(btn)` guard prevents the crash, but the active class is never set.

**Lines:** 4516 (_initStratMode call), 4518 (button lookup), 7009–7013 (pills created inside _sfRender)

**Fix:** Move the active-class setting logic into `_sfRender()` after the pills are created, and remove or no-op `_initStratMode` at startup.

---

### BUG-19 · Market page "loadSignalContext comment says CONTEXT but goes to UNDERSTAND
**Symptom:** Minor but confusing for developers. The comment at line 7380 says "Auto-navigate to CONTEXT pre-trade gate" but the code calls `showUnderstand()`.

**Root cause:** Comment was not updated when the navigation destination changed.

**Line:** 7380

**Fix:** Update comment to "Auto-navigate to UNDERSTAND tab with signal pre-loaded."

---

### BUG-20 · Portfolio VaR uses hardcoded 1.5% daily std for all assets
**Symptom:** Portfolio VaR is always computed as `portfolio_value × 1.645 × 0.015` regardless of what assets are in the portfolio. A portfolio of stable bonds shows the same risk as a portfolio of meme coins.

**Root cause:** Line 8239: `const portStd = 0.015; // 1.5% daily std — production computes from 252-day returns`. The comment acknowledges this is a stub.

**Line:** 8239

**Fix:** Call `GET /api/var` (which exists on the backend and computes real std from 252-day returns) instead of the local approximation.

---

## LOW — Minor issues

---

### BUG-21 · Unauthenticated backend routes: /api/send-sms, /api/pine-script, /api/pine-divergence, /api/pine-strategy
**Symptom:** These four routes have no `@login_required` decorator. Anyone who knows the URL can call them without being logged in.

**Root cause:** Routes at lines 5350, 5365, 5380, 5395 in `app.py` are missing `@login_required`.

**Note:** Pine script routes serve static files and may be intentionally public. `/api/send-sms` uses the caller's Twilio config so abuse has limited blast radius. Flag for review rather than blanket fix.

**Fix:** Add `@login_required` to `/api/send-sms` at minimum. Decide whether pine-script endpoints should be public or authenticated.

---

### BUG-22 · SIGNAL tab footer "Check Context → UNDERSTAND" is hidden until a signal is loaded — no visual indication
**Symptom:** First-time users see the SIGNAL tab with no obvious next-step button. The "Next" button at the bottom of the signals list is `display:none` until `sfUpdateFooter()` is called, which only happens after clicking Analyse on a card.

**Root cause:** Line 7070: `style="display:none"`. `sfUpdateFooter()` makes it visible. But the user has no visual cue that they need to click a card first before the Next button appears.

**Fix:** Consider showing a dimmed/disabled Next button with a tooltip "Select a signal above to continue" rather than hiding it completely.

---

### BUG-23 · Performance tab loads from /api/signals/history but displays "--" if no trades logged
**Symptom:** The PERFORMANCE tab shows all `--` values for new users who haven't run any analyses. No empty-state messaging.

**Root cause:** `showPerformance()` at line 9120 calls `dvFetch('/api/signals/history')` but if the result is empty or null, no placeholder message is shown.

**Lines:** 9097–9140 area

**Fix:** Add an empty state: "No signal history yet — run your first analysis to start tracking performance."

---

## SUMMARY TABLE

| ID | Severity | Area | One-line description |
|----|----------|------|----------------------|
| BUG-01 | CRITICAL | Auto-refresh | arSet duplicate — SIGNAL page auto-refresh completely broken |
| BUG-02 | CRITICAL | Auth | Login button bypasses /api/login — no real authentication |
| BUG-03 | CRITICAL | Signal flow | tp2/tp3 not mapped — SIZE tab TP2 and TP3 always blank |
| BUG-04 | CRITICAL | Navigation | UNDERSTAND back button calls showUnderstand not showSignalFeed |
| BUG-05 | CRITICAL | Navigation | CONTEXT page orphaned — not in flow, progress dots break |
| BUG-06 | HIGH | Navigation | Step labels wrong — two pages both say "Step 3 of 5" |
| BUG-07 | HIGH | State | _stratMode default is 'all' vs 'scalp' — pages disagree |
| BUG-08 | HIGH | Performance | Market page: 2.5s min wait + 10s timeout vs 0.8s/5s on SIGNAL |
| BUG-09 | HIGH | SIZE tab | SELL signals show "+-X%" instead of "-X%" |
| BUG-10 | HIGH | Context | IPO listings are hardcoded mock data shipped as live |
| BUG-11 | MEDIUM | Context | Session scores are UTC-hour estimates, not real market data |
| BUG-12 | HIGH | Portfolio | Portfolio tab uses localStorage, ignores PostgreSQL backend |
| BUG-13 | HIGH | Alerts | Alerts tab shows hardcoded mock data, no real system wired |
| BUG-14 | MEDIUM | Auth | Sign In HTML — missing closing `>` on div tag |
| BUG-17 | MEDIUM | Navigation | SIGNAL footer button label says CONTEXT but goes to UNDERSTAND |
| BUG-18 | MEDIUM | State | _initStratMode runs before strat pills exist — active class never set on load |
| BUG-20 | MEDIUM | Portfolio | VaR hardcoded 1.5% std for all assets — ignores actual volatility |
| BUG-21 | LOW | Security | 4 backend routes missing @login_required |
| BUG-22 | LOW | UX | Next button hidden until signal selected — no visual hint to user |
| BUG-23 | LOW | Performance | Performance tab shows "--" with no empty state message |

---

## FILES TO CHANGE

- `static/index-v2-prototype.html` — all frontend bugs above
- `app.py` — BUG-21 only (add @login_required to 4 routes)

---

*End of report. All line numbers reference `static/index-v2-prototype.html` unless noted.*
