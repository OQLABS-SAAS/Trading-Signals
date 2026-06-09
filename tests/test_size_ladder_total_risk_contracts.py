"""Contract tests: Size-tab multi-leg ladder must display a combined MAX TOTAL LOSS
number — the single most important safety number for a multi-leg basket trade.

Tests assert structural contracts of both:
  1. szLadderRender() — the ladder display function (rendered into the Size tab).
  2. _szConfirmTrade() — the pre-trade confirmation modal (shown before the GO button).

Both surfaces must show the combined max-loss (= sum of per-leg moneyAtRisk) and
its percentage of the trader's account size, with clear "all legs stop out" language.

All tests run from repo root (pytest cwd); Path is relative to that.
"""
from pathlib import Path

HTML = Path("static/index-v2-prototype.html").read_text()

# ─────────────────────────────────────────────────────────────────────────────
# Narrow scope: extract szLadderRender block
# ─────────────────────────────────────────────────────────────────────────────
_RENDER_START = "function szLadderRender()"
_RENDER_END   = "function szLadderRefresh("
_rs = HTML.index(_RENDER_START)
_re = HTML.index(_RENDER_END, _rs)
RENDER_BLOCK = HTML[_rs:_re]

# ─────────────────────────────────────────────────────────────────────────────
# Narrow scope: extract _szConfirmTrade block
# ─────────────────────────────────────────────────────────────────────────────
_CONFIRM_START = "function _szConfirmTrade(onConfirm){"
_CONFIRM_END   = "// Trade buttons now go through the confirmation card first."
_cs = HTML.index(_CONFIRM_START)
_ce = HTML.index(_CONFIRM_END, _cs)
CONFIRM_BLOCK = HTML[_cs:_ce]

# ─────────────────────────────────────────────────────────────────────────────
# 1. Ladder render: combined max-total-loss card exists and is multi-mode-only
# ─────────────────────────────────────────────────────────────────────────────

def test_ladder_render_has_max_total_loss_card_id():
    """The ladder render must inject a div with id szMaxTotalLossCard for the safety banner."""
    assert 'id="szMaxTotalLossCard"' in RENDER_BLOCK


def test_ladder_render_max_total_loss_card_has_worst_case_attribute():
    """The max-total-loss card must carry data-sz-worst-case=true so tests can locate it."""
    assert 'data-sz-worst-case="true"' in RENDER_BLOCK


def test_ladder_render_max_total_loss_card_is_multi_mode_only():
    """The card must be guarded by _isSingle — it must NOT appear in single-leg mode."""
    # The card is rendered inside an IIFE that returns '' for single mode.
    # We verify that _isSingle (or < 2 rows) is a guard before the card html.
    card_idx = RENDER_BLOCK.index('id="szMaxTotalLossCard"')
    # The guard check _isSingle must appear before the card string in this block.
    guard_idx = RENDER_BLOCK.rindex('_isSingle', 0, card_idx)
    assert guard_idx < card_idx, "_isSingle guard must precede the max-loss card"


def test_ladder_render_max_total_loss_shows_total_risk_dollar():
    """The dollar amount in the max-loss card must come from totalRisk (sum of all leg risks)."""
    assert 'id="szMaxTotalLossDollar"' in RENDER_BLOCK


def test_ladder_render_max_total_loss_dollar_formula_uses_totalRisk():
    """The dollar amount must be rendered from totalRisk, not a separate computation."""
    # Find the szMaxTotalLossDollar span and confirm totalRisk is used nearby.
    dollar_idx = RENDER_BLOCK.index('id="szMaxTotalLossDollar"')
    snippet = RENDER_BLOCK[dollar_idx:dollar_idx + 200]
    assert "totalRisk" in snippet


def test_ladder_render_max_total_loss_shows_pct_badge():
    """The percentage badge must exist and show % of account."""
    assert 'id="szMaxTotalLossPctBadge"' in RENDER_BLOCK


def test_ladder_render_max_total_loss_pct_formula():
    """The % badge must be computed as totalRisk / acct * 100 (via the local pct variable)."""
    # The badge renders `pct`, which is declared as totalRisk / acct * 100 in the IIFE.
    # We check that the pct variable assignment (the formula) exists in the card IIFE.
    card_idx = RENDER_BLOCK.index('id="szMaxTotalLossCard"')
    # The IIFE starts before the card, walk back to find `const pct = totalRisk / acct`
    iife_region = RENDER_BLOCK[max(0, card_idx - 600):card_idx + 400]
    assert "totalRisk / acct * 100" in iife_region
    # And the badge uses pct.toFixed(2) to render it
    badge_idx = RENDER_BLOCK.index('id="szMaxTotalLossPctBadge"')
    snippet = RENDER_BLOCK[badge_idx:badge_idx + 300]
    assert "pct.toFixed(2)" in snippet


def test_ladder_render_max_total_loss_says_worst_case_all_legs_stop():
    """The card header must include 'stop out' language so the meaning is unambiguous."""
    assert "stop out" in RENDER_BLOCK


def test_ladder_render_max_total_loss_card_uses_red_colour():
    """The card must use the red-family colour (#e8706e) for the dollar amount."""
    card_idx = RENDER_BLOCK.index('id="szMaxTotalLossCard"')
    # The dollar div is 80+ chars after the card opening — use a wider window
    snippet = RENDER_BLOCK[card_idx:card_idx + 800]
    assert "#e8706e" in snippet


def test_ladder_render_max_total_loss_guard_requires_2_or_more_legs():
    """The card must be hidden when there is only 1 row (_rowsToRender.length < 2)."""
    card_idx = RENDER_BLOCK.index('id="szMaxTotalLossCard"')
    # The IIFE guard must reference length < 2 before the card.
    guard_region = RENDER_BLOCK[max(0, card_idx - 400):card_idx]
    assert "< 2" in guard_region


def test_ladder_render_totalRisk_accumulated_across_rows():
    """totalRisk must be incremented inside the row map — i.e., per-leg accumulation."""
    assert "totalRisk += moneyAtRisk;" in RENDER_BLOCK


def test_ladder_render_moneyAtRisk_formula():
    """Each leg's moneyAtRisk must equal acct * (risk/100) — same as _szBuildExecutionLegs."""
    assert "acct * (risk/100)" in RENDER_BLOCK


# ─────────────────────────────────────────────────────────────────────────────
# 2. _szConfirmTrade modal: max-total-loss card shown before GO button
# ─────────────────────────────────────────────────────────────────────────────

def test_confirm_modal_has_max_loss_card_id():
    """The confirm modal must have a div with id szCfMaxLossCard."""
    assert 'id="szCfMaxLossCard"' in CONFIRM_BLOCK


def test_confirm_modal_max_loss_card_has_worst_case_attribute():
    """The confirm modal's max-loss card must carry data-sz-worst-case=true."""
    assert 'data-sz-worst-case="true"' in CONFIRM_BLOCK


def test_confirm_modal_max_loss_dollar_id():
    """The dollar amount in the confirm modal's max-loss card must have id szCfMaxLossDollar."""
    assert 'id="szCfMaxLossDollar"' in CONFIRM_BLOCK


def test_confirm_modal_max_loss_pct_id():
    """The % badge in the confirm modal must have id szCfMaxLossPct."""
    assert 'id="szCfMaxLossPct"' in CONFIRM_BLOCK


def test_confirm_modal_max_loss_dollar_uses_totRisk():
    """The confirm modal dollar figure must use totRisk (sum of all leg risks from _szBuildExecutionLegs)."""
    dollar_idx = CONFIRM_BLOCK.index('id="szCfMaxLossDollar"')
    snippet = CONFIRM_BLOCK[dollar_idx:dollar_idx + 200]
    assert "totRisk" in snippet


def test_confirm_modal_max_loss_pct_formula():
    """The confirm modal % must be totRisk / acct * 100."""
    pct_idx = CONFIRM_BLOCK.index('id="szCfMaxLossPct"')
    snippet = CONFIRM_BLOCK[pct_idx:pct_idx + 300]
    assert "totRisk" in snippet
    assert "acct" in snippet


def test_confirm_modal_max_loss_card_before_go_button():
    """The max-loss card must appear in the HTML before the GO button (szConfirmGo)."""
    card_idx = CONFIRM_BLOCK.index('id="szCfMaxLossCard"')
    go_idx   = CONFIRM_BLOCK.index('id="szConfirmGo"')
    assert card_idx < go_idx, "Max-loss card must precede the GO button in the modal"


def test_confirm_modal_max_loss_multi_leg_label_shows_n_legs():
    """For multi-leg trades (nT > 1), the card header must mention the number of legs."""
    # The label uses: nT>1 ? 'Max total loss — if ALL '+nT+' legs stop out' : '...'
    assert "legs stop out" in CONFIRM_BLOCK


def test_confirm_modal_max_loss_card_uses_red_colour():
    """The confirm modal's max-loss card must use the red border colour."""
    card_idx = CONFIRM_BLOCK.index('id="szCfMaxLossCard"')
    snippet = CONFIRM_BLOCK[card_idx:card_idx + 800]
    assert "rgba(232,112,110," in snippet


def test_confirm_modal_totRisk_from_szBuildExecutionLegs():
    """totRisk in the confirm modal must be computed by summing moneyAtRisk from _szBuildExecutionLegs legs."""
    # _szBuildExecutionLegs is called at the top and each leg's moneyAtRisk is summed.
    assert "_szBuildExecutionLegs" in CONFIRM_BLOCK
    # totRisk += l.moneyAtRisk — the summation loop
    assert "totRisk+=l.moneyAtRisk" in CONFIRM_BLOCK


def test_confirm_modal_account_size_used_for_pct():
    """The confirm modal must read account size from szAcct (same source as the ladder)."""
    assert "document.getElementById('szAcct')" in CONFIRM_BLOCK


# ─────────────────────────────────────────────────────────────────────────────
# 3. Formula consistency: ladder totalRisk and confirm totRisk use the same formula
# ─────────────────────────────────────────────────────────────────────────────

def test_ladder_and_confirm_both_use_acct_times_risk_pct():
    """Both the ladder and confirm modal must derive per-leg risk as acct * (riskPct/100)."""
    # Ladder: acct * (risk/100)
    assert "acct * (risk/100)" in RENDER_BLOCK
    # Confirm: totRisk is built from l.moneyAtRisk, which _szBuildExecutionLegs sets as acct*(r/100)
    build_start = HTML.index("function _szBuildExecutionLegs(){")
    build_end   = HTML.index("// ── Pre-trade confirmation card", build_start)
    build_block = HTML[build_start:build_end]
    assert "acct * (r / 100)" in build_block


def test_ladder_and_confirm_both_reference_same_account_input():
    """Both ladder render and confirm modal must read the account size from #szAcct."""
    assert "getElementById('szAcct')" in RENDER_BLOCK
    assert "getElementById('szAcct')" in CONFIRM_BLOCK
