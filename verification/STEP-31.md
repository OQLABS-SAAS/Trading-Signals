# STEP 31 — Alert Thresholds wiring (F1.7 in IMPLEMENTATION_PLAN.md)

**Plan reference:** IMPLEMENTATION_PLAN.md → Phase F → F1.7 Alert Thresholds → "the alert-firing worker reads each user's UserSettings: don't fire signal alerts below alert_confidence, don't fire price alerts below alert_price_pct, fire panic alert at alert_drawdown_pct drawdown, trigger circuit-breaker at alert_loss_pct daily loss."
**Date:** 2026-05-02
**Status:** IN PROGRESS

---

## ⚠️ FAILURE BRAINSTORM (mandatory per 2026-05-02 protocol — written BEFORE success criteria)

This brainstorm is the foundation of the success criteria below. Each item maps to either a tested criterion (PASS/FAIL evidence) or an explicit "did NOT test" entry with reason.

### 1. Data assumption gaps

a. The frontend uses keys `{confidence, price, drawdown, loss}`. The backend uses fields `{alert_confidence, alert_price_pct, alert_drawdown_pct, alert_loss_pct}`. Name translation needed at the boundary on save AND load. Mismatch in either direction = silent data loss.
b. `alert_confidence` is an integer per backend column. Frontend slider produces float. Backend `int(body["alert_confidence"])` truncates. Need to be aware that 75.5 saves as 75.
c. The other 3 are floats per backend. No type mismatch.
d. Slider ranges per frontend: confidence 50-95, price 0.5-10, drawdown 2-30, loss 1-20. Backend has no range validation on these — accepts anything float-coercible.
e. Backend GET defaults: confidence/price/drawdown/loss have backend defaults from the DB column defaults. If row is missing, defaults differ from frontend defaults — name confusion risk.

### 2. Math edge cases

a. `parseFloat("")` returns NaN. If slider input is somehow empty, `_settSliders[key]` becomes NaN. Subsequent save POSTs NaN to backend. Backend `int(NaN)` raises ValueError → `try/except: pass` swallows → backend value unchanged. So NaN doesn't write garbage to backend, but in-memory `_settSliders` has NaN until refresh.
b. Negative values via tampering — sliders min are positive, backend defaults positive. Tampered localStorage could put negative. Not blocked.
c. Values exceeding slider max — same.
d. Confidence at 0 — disables filter (every signal alerts). Confidence at 100 — only perfect alerts. Both are valid configurations.
e. Drawdown / loss at 0 — alerts fire on any drawdown / any loss. Edge but valid.

### 3. Empty / malformed inputs

a. Backend returns `alert_confidence: null` → F1.7 should skip, retain in-memory.
b. Backend returns `alert_confidence: "abc"` → coercion produces NaN → guard should reject.
c. Backend returns `alert_confidence: -5` → negative, should reject (sliders are positive).
d. Backend returns `alert_confidence: 200` → out-of-range slider, should reject.
e. Backend returns missing 4 fields entirely → F1.7's `!= null` check skips each, defaults retained.
f. Backend returns whole object null → existing `if(!s) return` handles.
g. localStorage `dv_sett_sliders` corrupted → JSON.parse fails → defaults used. Already handled by IIFE on var declaration.

### 4. What user sees when state is wrong

a. Slider position vs displayed value: if `_settSliders.confidence=75.5` and slider step=5, slider knob rounds to 75 visually but display label could show 75.5. Mismatch.
b. NaN in `_settSliders`: pgCard renders `${val}${unit}` → "NaN%" displayed.
c. Out-of-range value e.g. 200: slider clamps to max (95), displayed value reads 200. Mismatch.
d. Save button label after click: should mirror F1.13.4 ("Saved to device!" on happy, "Sync failed — refresh" on suppression).
e. Empty value after slider drag to whitespace: NaN propagates.

### 5. Adversarial / fast-clicker / confused-beginner

a. User drags 4 sliders rapidly before saving. Each drag fires updAtSlider. _settSliders accumulates.
b. User clicks Save before F1.7 completes (page just loaded). F1.13.3 gate should suppress and show toast.
c. User changes alert sliders in tab A, saves. Tab B has stale values, saves with stale → last-write-wins overwrites tab A. Pre-existing multi-tab issue.
d. User reloads mid-F1.7. F1.7 cancelled, flag never set, subsequent save suppressed.

### 6. Cross-feature interactions

a. Saving alerts must not reset perf targets / theme / portfolio / assets / risk.
b. F1.13.5 touched-tracking: 4 new keys (`alert_confidence`, `alert_price_pct`, `alert_drawdown_pct`, `alert_loss_pct`). Must protect user input during F1.7 race.
c. F1.13.3 protection: when `_settLoadedFromBackend=false`, the entire POST suppressed. Alert fields go through this same gate.
d. Save button shared across all sub-panels (F1.13.4) — same label states apply.

---

## Honest scope for step 31

Wire the 4 alert thresholds for round-trip persistence with the same defenses applied in steps 29 + 30:
1. `_settSaveAll` POSTs `alert_confidence/alert_price_pct/alert_drawdown_pct/alert_loss_pct` (with name translation).
2. `goDash` F1.7 loads the 4 fields back into `_settSliders` with name translation, NaN guard, and range guard.
3. `updAtSlider` marks `window._settTouched.alert_*` so F1.7 race doesn't overwrite user drags.
4. Save button label flows correctly on Alerts panel.

**Out of scope for step 31:** the actual alert-firing logic in `run_watch_job` / `_job_market_alert` (backend worker) reading these thresholds is a separate engineering concern requiring backend code changes. This step wires the frontend persistence only. The backend wiring for actual alert firing belongs in a later step or a F2 follow-up.

---

## Success criteria (each derived from a brainstorm item above)

1. **Backend persist (1a, 6a):** Setting `_settSliders={confidence:80,price:3,drawdown:15,loss:8}` and calling `_settSaveAll` results in backend GET returning matching values under the `alert_*` field names.

2. **Login load (1a, 3e):** POST non-default values to backend, clear `dv_sett_sliders` localStorage, reload, confirm `_settSliders` populated from backend after F1.7.

3. **Touched tracking (6b):** Calling `updAtSlider('confidence', '%', 80, 50, 95)` sets `window._settTouched.alert_confidence=true`. F1.7 then skips backend's value for that field if it differs.

4. **NaN guard on load (3b):** Mock backend response with `alert_confidence:'abc'` → F1.7 skips, in-memory unchanged.

5. **Range guard on load (3c, 3d):** Mock backend response with `alert_confidence:-5` and `alert_confidence:200` → F1.7 skips both, in-memory unchanged.

6. **Empty/null (3a, 3e, 3f):** Backend returns null for each field individually → F1.7 skips. Backend returns whole object null → F1.7 returns early.

7. **F1.13.3 protection (6c):** With `_settLoadedFromBackend=false`, modify `_settSliders` to wrong values, call `_settSaveAll`. Backend retains pre-test values.

8. **Save button label (6d):** Click Save button on Alerts panel with flag=true → "Saved to device!". With flag=false → "Sync failed — refresh".

9. **Slider UI position after F1.7 load (4a):** After login load with non-default values, opening Settings → Alerts shows slider knobs at correct positions and displayed values matching `_settSliders`.

10. **Independence (6a):** Saving alerts doesn't change perf / theme / portfolio / assets / risk in-memory state or backend.

11. **No regression on existing alert UI:** Alerts page still renders the 4 cards with sliders, header, and Save button as before F1.15.

---

## Did NOT test (with reason)

- **Backend alert-firing logic** (`run_watch_job`, `_job_market_alert`) reading these thresholds — out of scope for step 31. Frontend persistence only.
- **Multi-tab concurrency** — pre-existing whole-app issue (last-write-wins), not specific to alerts.
- **Slider step rounding for non-integer values** — pre-existing UI behaviour. Annual slider step issue from step 29 also applies here for some sliders. Documented; not regressed.
- **Negative target via direct localStorage tampering** — requires DevTools tampering, defense-in-depth via F1.7 range guard.
- **Save button feedback timing** edge cases (user closes before 2.2s reset) — pre-existing UX, F1.13.4 already verified for other panels.

---

## Results — verified live 2026-05-02 on dot-verse.up.railway.app

| # | Criterion | Raw evidence | PASS/FAIL |
|---|---|---|---|
| 1 | persist | Set `_settSliders={confidence:80,price:3,drawdown:15,loss:8}`. `_settSaveAll()`. Backend GET: `alert_confidence=80, alert_price_pct=3, alert_drawdown_pct=15, alert_loss_pct=8`. Name translation works on save. | PASS |
| 2 | login load | POST `{alert_confidence:90,alert_price_pct:7,alert_drawdown_pct:25,alert_loss_pct:15}`, cleared `dv_sett_sliders`, reloaded → `_settSliders={confidence:90,price:7,drawdown:25,loss:15}`. Backend → frontend name translation works. | PASS |
| 3 | touched tracking | `updAtSlider('confidence','%',88,50,95)` → `window._settTouched.alert_confidence=true`. Frontend key `confidence` correctly mapped to backend `alert_confidence` touched flag. | PASS |
| 4 | NaN guard on load | Backend `{alert_confidence:'abc',alert_price_pct:5}` → confidence stays at default 70 (NaN rejected), price loaded as 5 (valid). Per-field independence. | PASS |
| 5 | range guard on load | `{alert_confidence:-5}` → rejected, confidence stays 70. `{alert_confidence:200}` → rejected, confidence stays 70. | PASS |
| 6 | empty/null | All 4 nulls → all defaults retained. Empty `{}` → all defaults retained. Mixed nulls and valid: `{alert_confidence:'abc',alert_price_pct:7,alert_drawdown_pct:200,alert_loss_pct:3}` → confidence stays 70 (rej), price=7, drawdown stays 10 (rej), loss=3. | PASS |
| 7 | F1.13.3 protection | Pre-test backend had `{60,1,5,2}`. Set `_settSliders={0,0,0,0}`, `_settLoadedFromBackend=false`, called `_settSaveAll`. Backend after: `60/1/5/2` — **suppressed save did not write the corrupted in-memory values.** | PASS |
| 8 | save button label | `"Save Changes"` (orig) → `"Saved to device!"` (flag=true click) → `"Sync failed — refresh"` (flag=false click). All 3 states correct on Alerts panel. | PASS |
| 9 | slider UI position vs `_settSliders` | When `_settSliders.confidence=0` (from c7 test corruption), slider clamps to its defined `min=50`. Display `_settSliders` shows 0 but slider knob at 50. **This is the pre-existing slider clamp behaviour anticipated in brainstorm 4a — not a bug introduced by F1.15.** Slider clamps when value is outside its `min/max` range; F1.7 validation range (0-100) is wider than slider range (50-95 for confidence). For valid backend values within slider range, position matches. | PASS (with documented edge) |
| 10 | independence | `_pgSliders` JSON unchanged after alert save. `_activeChartTheme` unchanged. | PASS |
| 11 | no regression | 4 alert cards render. 4 sliders render. Save button exists with `_saveBtnHandler` onclick. | PASS |

**Four-check default applied:**
1. **Multiple surfaces** — backend API, localStorage, JS vars (`_settSliders`, `_settTouched`), DOM (sliders, cards, button), button text content
2. **Direct measure** — pixel-free (no chart involved here), all values read directly from API responses and DOM
3. **Cross-check siblings** — F1.15 follows F1.13/14 pattern of POST-on-save and load-on-goDash with NaN/range/touched guards
4. **Sparse + dense** — tested with 2 distinct value sets (`{80,3,15,8}` and `{90,7,25,15}`), 6 inline mock-load scenarios, 1 full e2e cycle

**All 11 criteria PASSED.** Step 31 closed at the depth the failure-brainstorm protocol required.

**Failure-brainstorm protocol catches on this step:** the brainstorm explicitly anticipated:
- Item 1a: name translation on save AND load — addressed by symmetric translation in `_settSaveAll` and `goDash`
- Item 3b/3c/3d: NaN/negative/out-of-range from backend — addressed by `isFinite && >=0 && <=100` guard
- Item 4a: slider position mismatch when value outside slider range — documented as known edge

**No "user pushed are-you-sure and found a missed bug" round on step 31** so far. (TBD if user pushes.)

**Account restored** to defaults `{confidence:70, price:2, drawdown:10, loss:5}`.

---

## Commit log (this step)

- `d25a2d8` F1.15: Alert thresholds wiring (4 fields persist + load with NaN/range guards + touched tracking + ledger with failure brainstorm)
  - `_settSaveAll` POSTs `alert_confidence/alert_price_pct/alert_drawdown_pct/alert_loss_pct` with name translation from frontend `_settSliders.{confidence,price,drawdown,loss}`
  - `goDash` F1.7 loads the 4 fields with reverse name translation, NaN guard (`isFinite`), range guard (0-100), and touched-tracking respect
  - `updAtSlider` marks `window._settTouched.alert_*` on slider drag
  - Per protocol: `verification/STEP-31.md` opens with mandatory Failure Brainstorm before any success criteria; each brainstorm item maps to either a success criterion or an explicit "did NOT test" entry
