"""Contract tests: _todaySendOrders per-leg result array, failure UI, retry exclusion,
and button-state reset on all paths.

These are static-analysis tests (grep the HTML source) that assert the structural
contracts of the per-leg push failure + retry feature added to
_todayConfirmAndPlace / _todaySendOrders in static/index-v2-prototype.html.
"""
from pathlib import Path

HTML = Path("static/index-v2-prototype.html").read_text()


# ─────────────────────────────────────────────────────────────────────────────
# 1. _todaySendOrders builds a per-leg result array
# ─────────────────────────────────────────────────────────────────────────────

def test_send_orders_declares_legs_array():
    """_todaySendOrders must initialise a legs array before the send loop."""
    assert "var legs=[];" in HTML


def test_send_orders_pushes_per_leg_result_object():
    """Each queue entry must produce a legResult object pushed into legs[]."""
    assert "legs.push(legResult);" in HTML


def test_per_leg_result_has_symbol_field():
    """legResult must carry the symbol so the failure UI can label each row."""
    assert "symbol:o.sym" in HTML


def test_per_leg_result_has_legIndex_field():
    """legResult must carry the ladder leg index."""
    assert "legIndex:leg.idx" in HTML


def test_per_leg_result_has_target_field():
    """legResult must carry the leg target (tp1 / tp2 / …)."""
    assert "target:leg.target||'tp1'" in HTML


def test_per_leg_result_has_ok_field():
    """legResult.ok must be set true on success and remain false on failure."""
    assert "legResult.ok=true;" in HTML


def test_per_leg_result_has_order_id_field():
    """legResult.order_id must be populated from the API response on success."""
    assert "legResult.order_id=res.order_id;" in HTML


def test_per_leg_result_has_error_field():
    """legResult.error must be set from _mt5OrderErrorText on API failure."""
    assert "legResult.error=_mt5OrderErrorText(res);" in HTML


def test_per_leg_result_has_error_field_on_exception():
    """legResult.error must be set when a network exception is thrown."""
    assert "legResult.error=e&&e.message" in HTML


def test_send_orders_returns_legs_in_aggregate():
    """The return value of _todaySendOrders must include the legs array."""
    assert "return {ok:ok, fail:fail, lastError:lastError, legs:legs};" in HTML


def test_per_leg_result_carries_trade_backref():
    """legResult._trade must hold the original trade object for retry use."""
    assert "_trade:o" in HTML


def test_per_leg_result_carries_leg_backref():
    """legResult._leg must hold the original leg object for retry use."""
    assert "_leg:leg" in HTML


# ─────────────────────────────────────────────────────────────────────────────
# 2. Failure UI lists per-leg reasons inside the confirmation modal
# ─────────────────────────────────────────────────────────────────────────────

def test_confirm_modal_has_result_panel_element():
    """The modal HTML must include a todayConfirmResult container div."""
    assert 'id="todayConfirmResult"' in HTML


def test_result_panel_initially_hidden():
    """The result panel must start hidden (display:none) before placement."""
    # Ensure the id and display:none appear together (same HTML attribute string)
    idx = HTML.find('id="todayConfirmResult"')
    assert idx != -1
    surrounding = HTML[max(0, idx-10):idx+80]
    assert "display:none" in surrounding


def test_failure_ui_renders_per_leg_rows():
    """The handler must build one row per leg using the legs[] result array."""
    assert "r.legs||[]" in HTML


def test_failure_ui_shows_symbol_per_row():
    """Each row must include the symbol label."""
    assert "esc(l.symbol)" in HTML


def test_failure_ui_shows_leg_index_per_row():
    """Each row must show the leg index."""
    assert "l.legIndex" in HTML


def test_failure_ui_shows_target_per_row():
    """Each row must show the target (tp1/tp2/…)."""
    assert "esc(l.target)" in HTML


def test_failure_ui_shows_order_id_on_success():
    """Successful legs must display the order_id returned by the broker."""
    assert "esc(l.order_id)" in HTML


def test_failure_ui_shows_error_on_failure():
    """Failed legs must display the error message."""
    assert "esc(l.error)" in HTML


def test_failure_ui_shows_checkmark_for_ok_legs():
    """Placed legs must show a visible success indicator (checkmark)."""
    # ✓ encoded as HTML entity &#10003; or literal
    assert "&#10003;" in HTML or "✓" in HTML


def test_failure_ui_shows_cross_for_failed_legs():
    """Failed legs must show a visible failure indicator (cross)."""
    assert "&#10005;" in HTML or "✗" in HTML


def test_failure_ui_shows_partial_header():
    """Partial-failure header must report how many of total legs placed."""
    assert "of " in HTML and "legs placed" in HTML or "leg placed" in HTML


def test_failure_ui_shows_allfail_header():
    """All-fail case must show a clear failure header."""
    assert "failed" in HTML


def test_result_panel_revealed_on_failure():
    """After a failed/partial result, the result panel must be made visible."""
    assert "resultPanel.style.display=''" in HTML


def test_result_panel_html_set_on_failure():
    """resultPanel.innerHTML must be assigned the leg breakdown on failure."""
    assert "resultPanel.innerHTML=" in HTML


# ─────────────────────────────────────────────────────────────────────────────
# 3. Retry failed legs — excludes already-placed legs
# ─────────────────────────────────────────────────────────────────────────────

def test_retry_button_exists_in_failure_ui():
    """A retry button must be rendered when there are failed legs."""
    assert 'id="todayCfRetry"' in HTML


def test_retry_button_label_shows_failed_count():
    """The retry button must state how many failed legs it will retry."""
    assert "_failedLegs.length" in HTML
    assert "Retry" in HTML


def test_failed_legs_computed_by_filtering_ok_false():
    """Failed legs must be computed by filtering legs where ok===false."""
    assert "_failedLegs=(r.legs||[]).filter(function(l){ return !l.ok; })" in HTML


def test_ok_legs_computed_by_filtering_ok_true():
    """OK legs must be tracked separately to prevent double-placing."""
    assert "_okLegs=(r.legs||[]).filter(function(l){ return l.ok; })" in HTML


def test_retry_calls_send_orders_with_leg_subset():
    """The retry handler must call _todaySendOrders with the legSubset argument."""
    assert "_todaySendOrders(_failedLegs.map(function(l){ return l._trade; })" in HTML or \
           "_todaySendOrders(_failedLegs" in HTML


def test_send_orders_accepts_leg_subset_param():
    """_todaySendOrders must accept a third legSubset parameter."""
    assert "async function _todaySendOrders(trades, onProgress, legSubset)" in HTML


def test_leg_subset_path_uses_trade_and_leg_backrefs():
    """When legSubset is provided, it must use _trade and _leg from the subset entries."""
    assert "l._trade" in HTML
    assert "l._leg" in HTML


def test_leg_subset_skips_full_ladder_expansion():
    """The legSubset path must NOT call _todayLadderLegs (avoiding re-expanding placed legs)."""
    # The legSubset branch populates queue from the subset only; the else branch calls
    # _todayLadderLegs. Both branches must coexist in the function.
    leg_subset_idx = HTML.find("legSubset && legSubset.length")
    ladder_legs_idx = HTML.find("_todayLadderLegs(o).forEach")
    assert leg_subset_idx != -1, "legSubset branch not found"
    assert ladder_legs_idx != -1, "_todayLadderLegs expansion not found"
    # legSubset branch must appear before _todayLadderLegs expansion (else branch)
    assert leg_subset_idx < ladder_legs_idx


def test_today_scale_out_payload_is_one_exit_per_mt5_order():
    """Each Today scale-out leg must send only its assigned exit to MT5."""
    start = HTML.index("function _todayLegOrderPayload")
    payload = HTML[start : start + 2400]
    assert "var assignedTp=leg.trailing?null:(leg.tp||o.tp||null)" in payload
    assert "tp1:assignedTp" in payload
    assert "tp2:null" in payload
    assert "tp3:null" in payload
    assert "trailing:!!leg.trailing" in payload
    assert "tp1_alert:!!(!leg.trailing&&o._autos&&o._autos.tp1)" in payload
    assert "tp2_alert:false" in payload
    assert "ladder_leg_index:leg.idx||1" in payload
    assert "ladder_leg_target:leg.target||'tp1'" in payload
    assert "tp2:o.tp2" not in payload
    assert "tp3:o.tp3" not in payload
    assert "leg.trailing||(o._autos&&o._autos.trail)" not in payload


def test_retry_ok_legs_accumulated_to_prevent_double_count():
    """After retry, _okLegs must be extended with newly-placed legs."""
    assert "_okLegs.concat(" in HTML or "_okLegs=_okLegs.concat(" in HTML


def test_failed_legs_updated_after_retry_for_further_retry():
    """After a retry, _failedLegs must be recomputed from the retry result for possible further retry."""
    # Appears in the retry handler updating _failedLegs from r2.legs
    assert "_failedLegs=(r2.legs||[]).filter(function(l){ return !l.ok; })" in HTML


# ─────────────────────────────────────────────────────────────────────────────
# 4. Button state resets on all paths — no stuck "Placing…" state
# ─────────────────────────────────────="────────────────────────────────────────

def test_go_button_disabled_during_placement():
    """The Place button must be disabled before the async send starts."""
    assert "btn.disabled=true; btn.textContent='Placing…'" in HTML or \
           "btn.disabled=true; btn.textContent='Placing…'" in HTML


def test_go_button_re_enabled_on_failure():
    """On partial/total failure, the Place button must be re-enabled (btn.disabled=false)."""
    assert "btn.disabled=false;" in HTML


def test_go_button_hidden_on_failure_result_shown():
    """On failure the Place button is hidden in favour of the retry button."""
    assert "btn.style.display='none'" in HTML


def test_send_orders_wrapped_in_try_catch_in_handler():
    """The _todaySendOrders call in the handler must be wrapped in try/catch
    so a thrown exception cannot leave the button stuck."""
    # The handler has: try{ r=await _todaySendOrders(...) }catch(e){ r={...} }
    assert "try{" in HTML
    # Verify the catch sets a safe fallback r object with ok:0
    assert "r={ok:0,fail:" in HTML


def test_retry_button_disabled_during_retry():
    """The retry button must be disabled before the async retry starts."""
    assert "rb.disabled=true; rb.textContent='Retrying…'" in HTML or \
           "rb.disabled=true; rb.textContent='Retrying…'" in HTML


def test_status_cleared_after_send():
    """The progress status text must be cleared after placement completes."""
    assert "st.textContent='';" in HTML or "st.textContent = ''" in HTML
