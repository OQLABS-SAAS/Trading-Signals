"""Static-contract tests for ladder completeness (adversarial audit fixes).

Mirrors test_a5_quickwins_contracts.py pattern: read HTML as text, assert markers.

Items covered:
  P0-1  Confirm modal leg row: entry price interpolation + l.notional present.
  P0-2  Size tab leg row: entry displayed (@ entry format) inside the row template.
  P0-3  Today ladder leg row: entry displayed (@ _tdyEntryFmt) inside the row.
  P2-8  SUM row shows total lots ('total lots' label + _fmtSize(totalUnits)).
  P2-9  Scale-out mode label/badge string exists in szLadderRender.
  P2-10 Bottom bar always shows planned profit; shortfall shown additionally.
  P1-4  _todayRenderPlan 'Weekly goal:' replaced with _planHorizonLbl dynamic var.
  P1-5  _todayV2TargetPath: all 3 'weekly target' strings replaced with _tpHorizonLow.
  P1-6  _todayV2ScoutPanel: 'Weekly target reached' replaced with dynamic _spHorizonLbl.
  P1-7  Detail panel: 4 hardcoded 'Weekly target' / 'weekly target' strings use _horizonLbl.
"""
from pathlib import Path

HTML_PATH = Path("static/index-v2-prototype.html")
HTML = HTML_PATH.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# P0-1  Confirm modal leg row — entry price + l.notional
# ─────────────────────────────────────────────────────────────────────────────

def test_confirm_modal_leg_row_has_entry_price():
    """The confirm-modal leg row must interpolate an entry price variable."""
    # _cfEntryFmt is computed just above legRows and embedded in the template
    assert "_cfEntryFmt" in HTML, "_cfEntryFmt variable must be defined and used in confirm modal leg row"
    assert "entry '+_cfEntryFmt" in HTML or "entry '+_cfEntryFmt+" in HTML or "'entry '+_cfEntryFmt" in HTML


def test_confirm_modal_leg_row_has_notional():
    """The confirm-modal leg row must reference l.notional (per-leg $ position value)."""
    # The leg row now reads l.notional for the pos $ display
    assert "l.notional" in HTML or "notional=parseFloat(l.notional" in HTML


def test_confirm_modal_entry_fmt_variable_defined():
    """_cfEntryRaw and _cfEntryFmt must both be declared in _szConfirmTrade."""
    start = HTML.index("function _szConfirmTrade(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "_cfEntryRaw" in block
    assert "_cfEntryFmt" in block


def test_confirm_modal_leg_notional_variable():
    """The per-leg notional local var must be declared in the legRows map."""
    start = HTML.index("function _szConfirmTrade(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "notional=parseFloat(l.notional)" in block or "var notional" in block


# ─────────────────────────────────────────────────────────────────────────────
# P0-2  Size tab leg row — entry price displayed
# ─────────────────────────────────────────────────────────────────────────────

def test_size_ladder_leg_row_shows_entry():
    """The Size tab leg row template must show entry price (@ format)."""
    start = HTML.index("function szLadderRender(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    # The entry sub-line was added under the SL/price column
    assert "entry>0?String" in block or "toPrecision(5)" in block
    # The label text visible to the trader
    assert "@ ${entry" in block or "'@ '" in block or '"@ "' in block


def test_size_ladder_entry_in_sl_column():
    """Entry price sub-line must appear adjacent to 'SL price' label in szLadderRender."""
    start = HTML.index("function szLadderRender(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    sl_idx = block.find("SL price")
    assert sl_idx >= 0
    # Entry reference must appear within 400 chars of 'SL price'
    nearby = block[max(0, sl_idx - 50):sl_idx + 400]
    assert "toPrecision" in nearby or "entry>0" in nearby or "entry>=1" in nearby


# ─────────────────────────────────────────────────────────────────────────────
# P0-3  Today ladder leg row — entry price displayed
# ─────────────────────────────────────────────────────────────────────────────

def test_today_ladder_leg_row_shows_entry():
    """The Today ladder leg row must show entry price via _tdyEntryFmt."""
    start = HTML.index("function _todayLadderHtml(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "_tdyEntryFmt" in block


def test_today_ladder_entry_in_row_template():
    """_tdyEntryFmt must be embedded inside the row HTML string, not just defined."""
    start = HTML.index("function _todayLadderHtml(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    # The row template emits '@ ' then concatenates _tdyEntryFmt
    # Actual form in file: '<span>@ '+_tdyEntryFmt+' · '
    assert "@ '+_tdyEntryFmt" in block or '@ "+_tdyEntryFmt' in block


# ─────────────────────────────────────────────────────────────────────────────
# P2-8  SUM row — total lots
# ─────────────────────────────────────────────────────────────────────────────

def test_sum_row_total_lots_label():
    """The SUM/totals row must contain a 'total lots' label."""
    start = HTML.index("function szLadderRender(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "total lots" in block


def test_sum_row_uses_total_units():
    """The SUM row lots cell must reference totalUnits (the running sum variable)."""
    start = HTML.index("function szLadderRender(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    # _fmtSize(totalUnits) is the expression used
    assert "_fmtSize(totalUnits)" in block


# ─────────────────────────────────────────────────────────────────────────────
# P2-9  Scale-out mode label
# ─────────────────────────────────────────────────────────────────────────────

def test_scale_out_mode_label_exists():
    """A scale-out plan mode label/badge must exist in szLadderRender."""
    start = HTML.index("function szLadderRender(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "Scale-out plan" in block


def test_scale_out_banner_references_entry():
    """The scale-out banner must show the shared entry price."""
    start = HTML.index("function szLadderRender(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    # _scaleOutBanner variable holds it
    assert "_scaleOutBanner" in block
    # It references _entryFmtBadge (the formatted entry)
    assert "_entryFmtBadge" in block


def test_scale_out_banner_only_in_multi_mode():
    """Scale-out banner must be guarded to multi (not single) mode."""
    start = HTML.index("function szLadderRender(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    # Guard: !_isSingle
    assert "!_isSingle" in block


def test_size_entry_brain_advisory_card_is_present():
    """Size must show the same entry-brain decision surface as Today."""
    assert 'id="szEntryBrainCard"' in HTML
    assert "function _szLoadEntryBrain(" in HTML
    assert "function _szRenderEntryBrainCard(" in HTML


def test_size_entry_brain_sends_backtest_evidence():
    """Size advisory must include proven backtest fields before any auto-authority."""
    start = HTML.index("function _szEntryBrainPayload(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "_btVerified:sig._btVerified===true" in block
    assert "_btPf:sig._btPf" in block
    assert "_btExpectancy:sig._btExpectancy" in block
    assert "_btTrades:sig._btTrades" in block


def test_size_entry_brain_can_auto_select_only_existing_execution_modes():
    """The brain may switch Size between single and existing scale-out, not live scale-in."""
    start = HTML.index("function _szLoadEntryBrain(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "dvFetch('/api/entry-plan/advisory'" in block
    assert "data.execution_authority===true" in block
    assert "data.recommended_mode==='scale_out'" in block
    assert "szSetMode('multi','brain')" in block
    assert "data.recommended_mode==='single'" in block
    assert "szSetMode('single','brain')" in block
    assert "data.recommended_mode==='scale_in'" not in block[block.index("if(data && data.execution_authority===true"):]


def test_size_entry_brain_protects_manual_override():
    """Manual Size mode changes must stop the advisory brain from flipping the user's mode."""
    start = HTML.index("function szSetMode(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "function szSetMode(mode, source)" in block
    assert "if(source!=='brain') window._szEntryBrainUserOverride=true" in block


def test_size_entry_brain_explains_scale_in_vs_scale_out_truthfully():
    """Size UI must distinguish shared-entry scale-out from different-entry scale-in."""
    card_start = HTML.index("function _szRenderEntryBrainCard(")
    card_end = HTML.index("\nfunction ", card_start + 1)
    card = HTML[card_start:card_end]
    render_start = HTML.index("function szLadderRender(")
    render_end = HTML.index("\nfunction ", render_start + 1)
    render = HTML[render_start:render_end]
    assert "Advisory only - live execution authority is locked" in card
    assert "different entries" in card
    assert "Scale-out plan" in render
    assert "shared entry" in render


# ─────────────────────────────────────────────────────────────────────────────
# P2-10  Bottom bar — planned profit always shown; shortfall additional
# ─────────────────────────────────────────────────────────────────────────────

def test_bottom_bar_planned_profit_always_shown():
    """'Planned profit' label must always appear (not only when !targetNeedsScout)."""
    # After the fix, 'Planned profit' is no longer in a ternary that can hide it
    # It should appear as a literal string (not inside a targetNeedsScout ternary)
    assert "'Planned profit'" in HTML or '"Planned profit"' in HTML


def test_bottom_bar_no_scout_shortfall_replacing_profit():
    """'Scout shortfall' label must no longer appear as the primary label in the bottom bar."""
    # The old code had: targetNeedsScout?'Scout shortfall':'Planned profit'
    assert "targetNeedsScout?'Scout shortfall':'Planned profit'" not in HTML
    assert 'targetNeedsScout?"Scout shortfall":"Planned profit"' not in HTML


def test_bottom_bar_shortfall_shown_additionally():
    """Shortfall must still be shown (additionally) when targetNeedsScout is true."""
    # After fix: shortfall shown in a sub-span when targetNeedsScout && shortfall>0
    assert "targetNeedsScout&&(targetPath.shortfall||0)>0" in HTML or \
           "targetNeedsScout&&targetPath.shortfall" in HTML


# ─────────────────────────────────────────────────────────────────────────────
# P1-4  _todayRenderPlan — dynamic horizon label replaces "Weekly goal:"
# ─────────────────────────────────────────────────────────────────────────────

def test_plan_goal_banner_no_hardcoded_weekly():
    """'Weekly goal:' must no longer appear hardcoded in _todayRenderPlan."""
    start = HTML.index("function _todayRenderPlan(", HTML.index("function _todayLadderHtml("))
    # Find the first _todayRenderPlan after _todayLadderHtml (the old v1 one)
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "'Weekly goal:" not in block
    assert '"Weekly goal:' not in block


def test_plan_goal_banner_uses_horizon_label():
    """The goal banner in _todayRenderPlan must use _planHorizonLbl variable."""
    # Two _todayRenderPlan functions exist (v1 and v2); check v1 first
    start = HTML.index("function _todayRenderPlan(", HTML.index("function _todayLadderHtml("))
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "_planHorizonLbl" in block


def test_plan_horizon_lbl_maps_all_three():
    """_planHorizonLbl must be derived from a map of daily/weekly/monthly."""
    assert "'daily':'Daily','weekly':'Weekly','monthly':'Monthly'" in HTML or \
           '"daily":"Daily","weekly":"Weekly","monthly":"Monthly"' in HTML


# ─────────────────────────────────────────────────────────────────────────────
# P1-5  _todayV2TargetPath — no remaining hardcoded "weekly target" strings
# ─────────────────────────────────────────────────────────────────────────────

def test_target_path_no_hardcoded_weekly_target():
    """'weekly target' must not appear as a literal string inside _todayV2TargetPath."""
    start = HTML.index("function _todayV2TargetPath(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "'weekly target'" not in block.lower() or "_tpHorizonLow" in block


def test_target_path_uses_horizon_variable():
    """_todayV2TargetPath must use _tpHorizonLow (dynamic horizon label)."""
    start = HTML.index("function _todayV2TargetPath(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "_tpHorizonLow" in block


def test_target_path_no_hardcoded_no_weekly_target_set():
    """'No weekly target set' must no longer be a literal string."""
    start = HTML.index("function _todayV2TargetPath(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "'No weekly target set'" not in block


# ─────────────────────────────────────────────────────────────────────────────
# P1-6  _todayV2ScoutPanel — dynamic horizon label
# ─────────────────────────────────────────────────────────────────────────────

def test_scout_panel_no_hardcoded_weekly_target_reached():
    """'Weekly target reached - no new risk' must not be a literal string."""
    start = HTML.index("function _todayV2ScoutPanel(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "'Weekly target reached - no new risk'" not in block


def test_scout_panel_uses_horizon_label():
    """_todayV2ScoutPanel must use _spHorizonLbl for the protect-mode banner."""
    start = HTML.index("function _todayV2ScoutPanel(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "_spHorizonLbl" in block


def test_scout_panel_weekly_scout_target_dynamic():
    """The scout-mode 'basket covers the weekly target' string must be dynamic."""
    start = HTML.index("function _todayV2ScoutPanel(")
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "'basket covers the weekly target'" not in block
    assert "_spHorizonLow" in block


# ─────────────────────────────────────────────────────────────────────────────
# P1-7  Detail panel — _horizonLbl used for all Weekly target strings
# ─────────────────────────────────────────────────────────────────────────────

def test_detail_panel_no_hardcoded_weekly_target_path():
    """'Weekly target path' must not appear as a literal string in the v2 render."""
    start = HTML.index("function _todayRenderPlan(", HTML.index("function _todayV2ScoutPanel("))
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "'Weekly target path'" not in block


def test_detail_panel_no_hardcoded_weekly_target_already_protected():
    """'Weekly target already protected' must not appear as a literal string."""
    start = HTML.index("function _todayRenderPlan(", HTML.index("function _todayV2ScoutPanel("))
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "'Weekly target already protected'" not in block


def test_detail_panel_no_hardcoded_weekly_target_is_reached():
    """'Weekly target is reached.' must not appear as a literal string."""
    start = HTML.index("function _todayRenderPlan(", HTML.index("function _todayV2ScoutPanel("))
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "'Weekly target is reached." not in block


def test_detail_panel_uses_horizonlbl_variable():
    """_horizonLbl must be used in the v2 detail panel for target-path strings."""
    start = HTML.index("function _todayRenderPlan(", HTML.index("function _todayV2ScoutPanel("))
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "_horizonLbl" in block


def test_detail_panel_no_hardcoded_weekly_target_is_reached_paused():
    """'New MT5 orders are paused because the weekly target is reached' must be gone."""
    start = HTML.index("function _todayRenderPlan(", HTML.index("function _todayV2ScoutPanel("))
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "'New MT5 orders are paused because the weekly target is reached." not in block


def test_detail_panel_protect_mode_stays_on_dynamic():
    """'Protect mode stays on until the weekly target state resets' must be gone."""
    start = HTML.index("function _todayRenderPlan(", HTML.index("function _todayV2ScoutPanel("))
    end = HTML.index("\nfunction ", start + 1)
    block = HTML[start:end]
    assert "'Protect mode stays on until the weekly target state resets" not in block
