"""Contract tests: _szLadderSubmitGo per-leg result capture, failure breakdown UI,
retry-failed-only behaviour, and status-never-stuck guarantees.

These are static-analysis tests that grep static/index-v2-prototype.html for the
structural contracts added to _szLadderSubmitGo in the Size/Act tab.  They mirror
the pattern of test_today_push_perleg_recovery_contracts.py (Today tab) so both
tabs are held to the same safety standard.

All tests run from the repo root (pytest's cwd); Path is relative to that.
"""
from pathlib import Path

HTML = Path("static/index-v2-prototype.html").read_text()

# ── narrow the scope to _szLadderSubmitGo so we don't pick up Today-tab strings ──
# We extract the block from the function declaration to the next top-level function.
_SUBMIT_START = "async function _szLadderSubmitGo() {"
_SUBMIT_END   = "function szTypeChange(){"          # first function after the block
_start = HTML.index(_SUBMIT_START)
_end   = HTML.index(_SUBMIT_END, _start)
BLOCK  = HTML[_start:_end]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Per-leg result array is captured during the submit loop
# ─────────────────────────────────────────────────────────────────────────────

def test_sz_per_leg_result_array_declared():
    """_szLegResults array must be declared before the send loop starts."""
    assert "var _szLegResults = [];" in BLOCK


def test_sz_ok_legs_array_declared():
    """_szOkLegs must be declared to track successfully-placed legs."""
    assert "var _szOkLegs = [];" in BLOCK


def test_sz_failed_legs_array_declared():
    """_szFailedLegs must be declared to track legs that failed."""
    assert "var _szFailedLegs = [];" in BLOCK


def test_sz_leg_result_has_symbol_field():
    """Each legResult must carry the signal symbol for the failure UI label."""
    assert "symbol: sig.sym," in BLOCK


def test_sz_leg_result_has_legIndex_field():
    """Each legResult must carry a legIndex for display and ordering."""
    assert "legIndex: leg.idx || (origIdx + 1)," in BLOCK


def test_sz_leg_result_has_target_field():
    """Each legResult must carry the target (tp1/tp2/…)."""
    assert "target: target," in BLOCK


def test_sz_leg_result_initialised_ok_false():
    """legResult must be initialised with ok: false before the fetch attempt."""
    assert "ok: false," in BLOCK


def test_sz_leg_result_initialised_order_id_null():
    """legResult must be initialised with order_id: null."""
    assert "order_id: null," in BLOCK


def test_sz_leg_result_initialised_error_null():
    """legResult must be initialised with error: null."""
    assert "error: null," in BLOCK


def test_sz_leg_result_ok_set_true_on_success():
    """legResult.ok must be set true when the API returns an order_id."""
    assert "legResult.ok = true; legResult.order_id = res.order_id;" in BLOCK


def test_sz_leg_result_error_set_from_api_on_failure():
    """legResult.error must be set from _mt5OrderErrorText on API failure."""
    assert "legResult.error = _mt5OrderErrorText(res);" in BLOCK


def test_sz_leg_result_error_set_on_exception():
    """legResult.error must be set when a network exception is thrown."""
    assert "legResult.error = e && e.message ? e.message" in BLOCK


def test_sz_leg_results_pushed_to_arrays_in_loop():
    """After each leg, legResult must be pushed to _szLegResults and partitioned."""
    assert "_szLegResults.push(legResult);" in BLOCK
    assert "if (legResult.ok) _szOkLegs.push(legResult); else _szFailedLegs.push(legResult);" in BLOCK


# ─────────────────────────────────────────────────────────────────────────────
# 2. Per-leg breakdown UI is rendered into szLadderStatus
# ─────────────────────────────────────────────────────────────────────────────

def test_sz_status_element_exists_in_html():
    """The szLadderStatus div must exist in the HTML."""
    assert 'id="szLadderStatus"' in HTML


def test_sz_render_leg_status_function_exists():
    """_szRenderLegStatus must be defined inside _szLadderSubmitGo."""
    assert "function _szRenderLegStatus()" in BLOCK


def test_sz_render_uses_ok_and_failed_arrays():
    """_szRenderLegStatus must read from _szOkLegs and _szFailedLegs."""
    assert "var ok = _szOkLegs.length, fail = _szFailedLegs.length;" in BLOCK


def test_sz_render_concatenates_all_results():
    """_szRenderLegStatus must concat ok and failed legs for display."""
    assert "var allResults = _szOkLegs.concat(_szFailedLegs);" in BLOCK


def test_sz_render_shows_symbol_per_row():
    """Each row in the breakdown must show the symbol."""
    assert "esc(l.symbol)" in BLOCK


def test_sz_render_shows_leg_index_per_row():
    """Each row must show the leg index."""
    assert "l.legIndex" in BLOCK


def test_sz_render_shows_target_per_row():
    """Each row must show the target (tp1/tp2/…)."""
    assert "esc(l.target)" in BLOCK


def test_sz_render_shows_order_id_on_success():
    """Successful rows must display the order_id."""
    assert "esc(l.order_id)" in BLOCK


def test_sz_render_shows_error_on_failure():
    """Failed rows must display the error text."""
    assert "esc(l.error)" in BLOCK


def test_sz_render_shows_checkmark_for_ok():
    """Placed legs must show a visible success indicator (&#10003; / ✓)."""
    assert "&#10003;" in BLOCK


def test_sz_render_shows_cross_for_failed():
    """Failed legs must show a visible failure indicator (&#10005; / ✗)."""
    assert "&#10005;" in BLOCK


def test_sz_render_shows_partial_header():
    """Partial-failure header must name how many of total were placed."""
    assert "of " in BLOCK and "legs placed" in BLOCK


def test_sz_render_shows_allfail_header():
    """All-fail header must report that all legs failed."""
    assert "All " in BLOCK and " failed" in BLOCK


def test_sz_render_status_html_assigned():
    """status.innerHTML must be assigned the full breakdown."""
    assert "status.innerHTML = " in BLOCK


# ─────────────────────────────────────────────────────────────────────────────
# 3. Retry failed legs — only failed legs are re-sent; placed legs excluded
# ─────────────────────────────────────────────────────────────────────────────

def test_sz_retry_button_element_id():
    """A retry button with id szLadderRetryBtn must be injected on failure."""
    assert 'id="szLadderRetryBtn"' in BLOCK


def test_sz_retry_button_label_contains_fail_count():
    """The retry button label must reflect the number of failed legs."""
    # The button text includes: 'Retry ' + fail + ' failed leg'
    assert "Retry ' + fail + ' failed leg" in BLOCK


def test_sz_retry_iterates_only_failed_legs():
    """Retry loop must iterate _szFailedLegs, not re-expand _szBuildExecutionLegs."""
    assert "for (var ri = 0; ri < _szFailedLegs.length; ri++)" in BLOCK
    # The retry onclick handler must use _szSendOneLeg(fl._legSnapshot, ...) and
    # must NOT call _szBuildExecutionLegs() inside the onclick closure itself.
    # We find the onclick assignment and check the bounded closure body.
    onclick_start = BLOCK.index("retryBtn.onclick = async function()")
    onclick_body  = BLOCK[onclick_start:]
    # The closure ends at the matching brace — we can check conservatively that
    # _szBuildExecutionLegs is only referenced in comments within this scope, not
    # as an actual call.  The comment text uses the bare name without "()"; any
    # actual call would include the trailing "()".
    # Find the body up to the close of the retry wire block (starts at "if (fail > 0)")
    wire_start = BLOCK.index("if (fail > 0) {")
    wire_body  = BLOCK[wire_start:wire_start + 800]   # well within the wire block
    assert "_szBuildExecutionLegs()" not in wire_body


def test_sz_retry_uses_leg_snapshot_backref():
    """Retry must reconstruct requests from the stored _legSnapshot, not from live UI state."""
    assert "_legSnapshot: leg," in BLOCK            # stored at result-capture time
    assert "fl._legSnapshot" in BLOCK               # retrieved at retry time


def test_sz_retry_uses_orig_idx_backref():
    """Retry must use _origIdx for the _szLadderAuto lookup to match first-run settings."""
    assert "_origIdx: origIdx" in BLOCK
    assert "fl._origIdx" in BLOCK


def test_sz_retry_ok_legs_accumulated():
    """After retry, newly placed legs must be merged into _szOkLegs (prevents double-count)."""
    assert "_szOkLegs = _szOkLegs.concat(newOk);" in BLOCK


def test_sz_retry_failed_legs_updated_for_further_retry():
    """After retry, _szFailedLegs must be updated to only the still-failing legs."""
    assert "_szFailedLegs = newFail;" in BLOCK


def test_sz_retry_calls_render_after_retry():
    """After retry, _szRenderLegStatus must be called to refresh the display."""
    # Must appear AFTER the newOk/newFail merge
    merge_idx  = BLOCK.index("_szFailedLegs = newFail;")
    render_idx = BLOCK.index("_szRenderLegStatus();", merge_idx)
    assert render_idx > merge_idx


def test_sz_retry_navigates_to_act_when_all_clear():
    """When all legs are placed after retry, the app must navigate to the Act tab."""
    assert "if (_szFailedLegs.length === 0 && _szOkLegs.length > 0)" in BLOCK
    # And navigation calls are present in that block
    assert "setNav('act')" in BLOCK


def test_sz_no_build_execution_legs_inside_send_one_leg():
    """_szSendOneLeg must not call _szBuildExecutionLegs — it works from a single leg arg."""
    send_start = BLOCK.index("async function _szSendOneLeg(leg, origIdx)")
    # Find the closing brace — the function ends before _szRenderLegStatus
    render_start = BLOCK.index("function _szRenderLegStatus()", send_start)
    send_block = BLOCK[send_start:render_start]
    assert "_szBuildExecutionLegs" not in send_block


# ─────────────────────────────────────────────────────────────────────────────
# 4. Status never stuck — all paths resolve to a final UI state
# ─────────────────────────────────────────────────────────────────────────────

def test_sz_submit_wrapped_in_try_catch():
    """The main submit loop must be wrapped in try/catch so exceptions update status."""
    assert "try {" in BLOCK
    assert "} catch(e) {" in BLOCK


def test_sz_catch_updates_status_on_unexpected_throw():
    """The outer catch must write an error message into the status element."""
    # The catch block sets status.innerHTML with an error message
    assert "status.innerHTML = '<span style=" in BLOCK
    # and references the caught error
    assert "_escHtml(e && e.message" in BLOCK


def test_sz_render_called_after_main_loop():
    """_szRenderLegStatus must be called unconditionally after the send loop."""
    loop_end = BLOCK.index("var okCount = _szOkLegs.length")
    render_call = BLOCK.index("_szRenderLegStatus();", loop_end)
    assert render_call > loop_end


def test_sz_submitting_status_set_before_loop():
    """'Submitting N orders…' must appear BEFORE the main send loop."""
    # The "Submitting N orders…" banner is set right before the try/for loop at
    # the bottom of _szLadderSubmitGo (after _szSendOneLeg and _szRenderLegStatus
    # are defined).  The main loop begins at "for (var i = 0; i < legs.length".
    submitting_idx = BLOCK.index("Submitting ")
    main_loop_idx  = BLOCK.index("for (var i = 0; i < legs.length; i++)")
    assert submitting_idx < main_loop_idx


def test_sz_early_return_on_no_legs_shows_message():
    """If _szBuildExecutionLegs returns empty, a clear error must be shown before any fetch."""
    assert "Enter entry and stop loss before submitting" in BLOCK


def test_sz_all_success_navigates_to_act():
    """When all legs succeed on first try, the function navigates to the Act tab."""
    assert "if (okCount > 0 && failCount === 0)" in BLOCK
    nav_idx = BLOCK.index("if (okCount > 0 && failCount === 0)")
    act_idx  = BLOCK.index("setNav('act')", nav_idx)
    assert act_idx > nav_idx


def test_sz_partial_success_does_not_navigate():
    """Partial success must NOT navigate away — user stays in Size tab to retry."""
    # The navigation guard is `if (okCount > 0 && failCount === 0)` — partial
    # failure (failCount > 0) falls through without navigation.
    # Confirm there is no unconditional setNav call outside the guard.
    guard_idx = BLOCK.index("if (okCount > 0 && failCount === 0)")
    # All occurrences of setNav in BLOCK must be inside the guard or inside retry
    nav_positions = [i for i in range(len(BLOCK)) if BLOCK[i:i+len("setNav('act')")] == "setNav('act')"]
    assert nav_positions, "setNav('act') must appear at least once"
    for pos in nav_positions:
        # Each must be after some guard (either okCount guard or _szFailedLegs===0 guard)
        preceding = BLOCK[:pos]
        assert (
            "if (okCount > 0 && failCount === 0)" in preceding or
            "if (_szFailedLegs.length === 0 && _szOkLegs.length > 0)" in preceding
        ), f"setNav at position {pos} is not inside a failCount===0 guard"


def test_sz_order_parameters_unchanged():
    """Order body fields must match the original implementation (no sizing changes)."""
    # Verify that all original body fields are still present
    assert "ticker: sig.sym" in BLOCK
    assert "order_type: orderType" in BLOCK
    assert "direction: direction" in BLOCK
    assert "asset_type: assetType" in BLOCK
    assert "entry: entry" in BLOCK
    assert "sl: sl" in BLOCK
    assert "tp1: assignedTp" in BLOCK
    assert "entry_confluence: _entryConf" in BLOCK
    assert "entry_atr:        _entryAtr" in BLOCK
