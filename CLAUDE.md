# DotVerse — Claude Working Protocol

---

## THE SIX STOP GATES
### Answer every gate before touching anything. One NO = full stop.

| Gate | Question | If NO |
|---|---|---|
| 1 | Was I explicitly asked to do this? | Stop. Report. Ask. |
| 2 | Can I state the symptom, root cause, and mechanism? | Investigate first. No fix yet. |
| 3 | Have I written a valid plan and got explicit confirmation? | Write plan. Wait. |
| 4 | Am I certain or assuming? | Label it. Tell user. Ask to proceed. |
| 5 | Have I stated what could go wrong? | State risks now. |
| 6 | Is this verified at runtime or only code reading? | State Level 4. Do not claim verified. |

---

## WORKING AGREEMENT

**Before every session:** User says "Protocol active." Claude reads the six gates before responding to anything.

**Before every fix — Claude must state all five or the gate does not open:**
1. The problem
2. The root cause
3. The exact change and why
4. What could break
5. How it will be verified

**Task discipline:** One task at a time. Fully closed before the next opens.

**You hold the gate:** If any of the five are missing, reject it.

---

## MANDATORY MINDSET
- Think before acting — not act then explain
- Break complex tasks into substeps
- Show plan before executing
- Anticipate edge cases and dependencies
- Document as you go
- Provide status updates
- Verify against the original requirement

**Approach: Thorough → Systematic → Planned → Executed → Verified**

---

## CORE RULES — NON-NEGOTIABLE

### Bug Reports
- Do NOT open files immediately
- Do NOT start grepping
- First: reason out loud about the full user flow affected
- Then: identify what you need to verify before forming a conclusion
- Then: look at code to verify, not to fix

### Scope Discipline
- State precisely which files will be changed and why
- State precisely what will NOT be changed
- If a new issue is discovered mid-task: STOP — report it, ask whether to include it
- Never expand scope mid-task without explicit user approval
- One confirmation = one scope

### Understanding Before Acting
- Never assume intent — restate the requirement in your own words before starting
- If the instruction is ambiguous, ask one clarifying question before proceeding
- Do not infer scope from similar past tasks — treat every task as new

### Verification Hierarchy
"Verified" has a strict definition. In descending order of reliability:
1. **Runtime proof** — observed behaviour in a running browser/server
2. **Console/log evidence** — instrumentation confirming value or code path at execution time
3. **Execution trace** — manually stepping through every branch with real data values
4. **Code reading only** — weakest form; must be labelled "unverified assumption" when used

Static code analysis (grep, read, eyeball) is Level 4. Never sufficient alone for a bug fix. Always state which level of verification was used.

### Confidence Labelling
Every conclusion must carry an explicit label:
- **CONFIRMED** — verified at runtime or with instrumentation
- **LIKELY** — full execution trace completed, no contradicting evidence
- **HYPOTHESIS** — reasoning from code reading, not yet traced
- **UNCERTAIN** — incomplete information, state what is missing

Never present a hypothesis with the same tone as a confirmed fact.

### Completion Criteria
A task is only "done" when:
1. The fix is in the file (not just stated)
2. A verification method was stated and executed
3. The original requirement was re-read and matched
4. The user was told which verification level was reached

### Session Resume Rule
- Treat any context summary as a starting point, not ground truth
- Re-read relevant source files before forming any opinion
- Never state a conclusion about code behaviour based on summary alone
- If summary says something was fixed, verify it is actually in the file

### The "I Already Know This" Rule
Prior context, similar bugs, or pattern recognition never substitutes for tracing the current problem fresh. Every bug gets a full trace from scratch. Assumptions built on memory are the most common source of wrong fixes.

### Investigation Gate
For any task requiring more than 3 tool calls to investigate:
1. State the investigation plan upfront
2. List what questions need answering and how
3. Get user go-ahead before starting
4. Report findings before proposing fixes

Do not silently investigate then present conclusions and fixes together as if the investigation was obvious.

---

## QUICK REFERENCE — KEY RULES BY SITUATION

| Situation | Rule |
|---|---|
| Bug reported | Don't open files. Reason out loud first. |
| Session resumed | Re-read source files. Summary is not ground truth. |
| Ambiguous instruction | Ask one clarifying question. Do not infer. |
| Investigation needed | State plan. Get go-ahead. Report findings first. |
| Fix fails | Do not silently try another fix. Stop and report. |
| Architectural change | State all downstream effects before touching anything. |
| Long task | Break into substeps. Confirm scope at each stage. |
| Code copying | State what the code does before pasting it. Verify it fits. |
| Risk dismissal | Never skip risk statement. "Low risk" must be argued, not assumed. |
| Fix proposal | Five elements required: problem, root cause, change, risk, verification. |

---

## SELF-AUDIT RULE
After writing any fix, re-read the original user requirement and ask:
**"Have I verified this works at runtime, or only that the code looks correct?"**
Static code analysis is not verification.

---

## KNOWN BUGS — READ THIS FIRST EVERY SESSION

These are unresolved bugs confirmed by the user. Do not mark any as fixed until runtime verified in a live browser.

---

### BUG 1 — RSI Divergence Trendlines Not Rendering
**Status:** RESOLVED — runtime verified by user on 2026-04-12. Deployed to Railway.
**Fix summary:** RSI panel height increased 90px → 160px. Flat-line guard added (if y-spread < 5px, draw at midpoint y). Pivot dot radius increased 3.5px → 5.5px. Root cause was sub-pixel line height due to small RSI value differences on tiny canvas.

---

### BUG 2 — Scanner → Signals Chart Zero-Width (RESOLVED)
**Status:** RESOLVED — runtime verified by user on 2026-04-12. Deployed to Railway.
**Fix summary:** `autoSize: true` in `_lwcCommonOpts`, `requestAnimationFrame` in `scannerLoadTicker`, all scanner entry points now use `scannerLoadTicker`.

---

### BUG 3 — `doAnalyze` Called Directly on 3 Code Paths (UNRESOLVED)
**Status:** UNRESOLVED as of 2026-04-11
**Symptom:** Lines 3252, 3263, 3317 in `index.html` call `doAnalyze` directly without going through `scannerLoadTicker`. If triggered while the signals tab is hidden, the chart renders into a zero-width container — same class of bug as BUG 2.
**Where to look:** History chip handler, instrument chip handler, sidebar ticker handler.

---

### BUG 4 — `/api/backtest` Missing `@login_required` (UNRESOLVED)
**Status:** UNRESOLVED as of 2026-04-11
**Symptom:** `app.py` line 3532 — `backtest_route` has no `@login_required` decorator. Unauthenticated users can call `/api/backtest` directly.

---

### SESSION HANDOFF NOTES — 2026-04-11
- User has been working 20+ hours. RSI divergence trendlines have been reported and "fixed" multiple times with no runtime verification. This is the primary unresolved issue.
- Git push failed due to HTTPS credentials — user must run `git push origin main` manually.
- `renderResults()` (old legacy function, ~lines 3413–3630) is dead code never called from `quickLoad`. Safe to remove eventually but not urgent.
- When user returns: ask them to say "Protocol active", then go straight to BUG 1 investigation — do NOT act before tracing the full render path.

---

### SESSION HANDOFF NOTES — 2026-04-12
**DotVerse (Railway — git push origin main):**
- BUG 1 (RSI divergence trendlines) — RESOLVED, runtime verified by user, deployed.
- BUG 2 (Scanner → Signals zero-width chart) — RESOLVED, runtime verified by user, deployed.
- BUG 3 and BUG 4 still UNRESOLVED — not touched this session.

**Quantverse PWA (Netlify — drag quantverse-pwa/ folder into Netlify deploy section):**
- Replaced 15-indicator TV-style vote engine with 7 strategy engines: Momentum, SMC/ICT, Price Action, Mean Reversion, Volume, Breakout, Harmonic Patterns.
- All signals computed locally from Binance/Frankfurter candles — no backend dependency.
- Strategy tab row added above ticker chips. Ticker chips now trigger on-demand analysis via `analyzeSym(sym)` → `analyzeInstrument(cfg)` → `runStrategy()`.
- Removed all DotVerse backend integration (authCheck, analyzeTicker, mapDvToSig, showOverlay).
- manifest.json and SW registration fixed for Netlify (start_url /, icons /icon-*.png, sw.js at /).
- Bug fixed this session: JSON.stringify in onclick HTML attribute caused SyntaxError on every ticker tap. Fixed by adding `analyzeSym(sym)` wrapper — no JSON in HTML attributes.
- Committed: 0f16861 (full rewrite), 9ee9ad4 (onclick fix).
- Verified at Level 4 (code reading) + user confirmed console errors were resolved after redeploying.

**Deploy reminder:**
- DotVerse: `git push origin main` → Railway auto-deploys.
- Quantverse: drag `quantverse-pwa/` folder into Netlify site's deploy section (NOT git push).
